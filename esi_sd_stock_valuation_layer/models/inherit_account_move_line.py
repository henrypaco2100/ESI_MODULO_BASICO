
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet
import datetime
import pytz
class SdInheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.company.sd_date_ini_management:
            user_tz = self.env.user.tz
            local = pytz.timezone(user_tz)
            domain.append(['date', '>=', pytz.utc.localize(self.env.company.sd_date_ini_management).astimezone(local).date()])
        return super(SdInheritAccountMoveLine, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.company.sd_date_ini_management:
            user_tz = self.env.user.tz
            local = pytz.timezone(user_tz)
            domain.append(['date', '>=', pytz.utc.localize(self.env.company.sd_date_ini_management).astimezone(local).date()])
        res = super(SdInheritAccountMoveLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                             orderby=orderby, lazy=lazy)
        return res