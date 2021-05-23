from django.db import models
from django.conf import settings
from django.shortcuts import reverse
from django.utils.text import slugify

from core import models as core_models
from activity import models as activity_models
from . import paytm as ptm

# Create your models here.


class Transaction(models.Model):
    call_back_url = None

    class payment_stat(models.IntegerChoices):
        fail = 0
        success = 1
        processing = 2

    # activity = models.ForeignKey(activity_models.Activity, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(
        default=100.00, decimal_places=2, max_digits=10)

    timestamp = models.DateTimeField(auto_now_add=True)

    order_id = models.CharField(
        unique=True, max_length=100, null=True, blank=True)
    checksum = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.PositiveSmallIntegerField(
        choices=payment_stat.choices, default=2)

    def save(self, *args, **kwargs):
        if self.order_id is None and self.made_on and self.id:
            self.order_id = self.made_on.strftime(
                'PAY2CHURCH%Y%m%dODR') + str(self.id)
        return super().save(*args, **kwargs)

    def _get_params(self, call_back_url=None):
        if not self.call_back_url:
            call_back_url = 'http://127.0.0.1:8000/callback/'
        params = {
            'MID': settings.PAYTM_MERCHANT_ID,
            'ORDER_ID': str(self.order_id),
            'CUST_ID': str(self.user.email),
            'TXN_AMOUNT': str(self.amount),
            'CHANNEL_ID': settings.PAYTM_CHANNEL_ID,
            'WEBSITE': settings.PAYTM_WEBSITE,
            # 'EMAIL': request.user.email,
            # 'MOBILE_N0': '1111111111',
            'INDUSTRY_TYPE_ID': settings.PAYTM_INDUSTRY_TYPE_ID,
            'CALLBACK_URL': call_back_url,
            # 'PAYMENT_MODE_ONLY': 'NO',
        }
        return params

    def gen_checksum(self):
        checksum = ptm.generate_checksum(
            self._get_params(), settings.PAYTM_SECRET_KEY)
        return checksum

    def get_params(self):
        params = self._get_params()
        params['CHECKSUMHASH'] = self.gen_checksum()
        return params

    def response_check(self, params):
        paytm_params = {}
        paytm_checksum = params['CHECKSUMHASH'][0]
        response_code = params['RESPCODE'][0]
        status = params['STATUS'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        is_valid_checksum = ptm.verify_checksum(
            paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum and response_code == '01':
            self.payment_status = 1
        if status == 'PENDING':
            self.payment_status = 2
        else:
            self.payment_status = 0
        return paytm_params
