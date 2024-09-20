odoo.define('plantation.dynamic_fields', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._updateFieldVisibility();
                self.$el.find("[name='amount_select']").on('change', function () {
                    self._updateFieldVisibility();
                });
            });
        },
        _updateFieldVisibility: function () {
            var amountSelectValue = this.$el.find("[name='amount_select']").val();

            // Hide all fields first
            this.$el.find("[name='amount_percentage_base']").closest('.o_field_widget').hide();
            this.$el.find("[name='quantity']").closest('.o_field_widget').hide();
            this.$el.find("[name='amount_fix']").closest('.o_field_widget').hide();
            this.$el.find("[name='amount_python_compute']").closest('.o_field_widget').hide();
            this.$el.find("[name='amount_percentage']").closest('.o_field_widget').hide();

            // Show the relevant field based on the selected value
            if (amountSelectValue === 'percentage') {
                this.$el.find("[name='amount_percentage_base']").closest('.o_field_widget').show();
                this.$el.find("[name='amount_percentage']").closest('.o_field_widget').show();
            } else if (amountSelectValue === 'quantity') {
                this.$el.find("[name='quantity']").closest('.o_field_widget').show();
            } else if (amountSelectValue === 'fix') {
                this.$el.find("[name='amount_fix']").closest('.o_field_widget').show();
            } else if (amountSelectValue === 'code') {
                this.$el.find("[name='amount_python_compute']").closest('.o_field_widget').show();
            }
        },
    });
});
