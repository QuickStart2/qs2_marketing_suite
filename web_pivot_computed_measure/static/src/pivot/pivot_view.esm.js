/** @odoo-module **/

import {PivotController} from "@web/views/pivot/pivot_controller";
import {DropdownItemCustomMeasure} from "@web_pivot_computed_measure/dropdown_item_custom_measure/dropdown_item_custom_measure.esm";
const { patch } = require("@web/core/utils/patch");

patch(PivotController.prototype, "web_pivot_computed_measure.PivotView", {
    /**
     * Add computed_measures to context key to avoid loosing info when saving the
     * filter to favorites.
     *
     * @override
     */
    getContext() {
        var res = this._super(...arguments);
        res.pivot_computed_measures = this.model._computed_measures;
        return res;
    },
});

PivotController.components.DropdownItemCustomMeasure = DropdownItemCustomMeasure;
