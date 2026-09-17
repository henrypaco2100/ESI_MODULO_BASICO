odoo.define('stock.report_visibility', function (require) {
    "use strict";

    var core = require('web.core');
    var ActionManager = require('web.ActionManager');

    ActionManager.include({
        _updateControlPanel: function () {
            this._super.apply(this, arguments);
            var self = this;
            var printMenu = this.$('.o_report_print');
            var isReportVisible = false;

            var settingValue = core._t.database.parameters.stock_sd_reportes_transf_interna;

            if (settingValue === 'True') {
                isReportVisible = true;
            }

            if (!isReportVisible) {
                printMenu.addClass('d-none');
            } else {
                printMenu.removeClass('d-none');
            }
        },
    });
});
