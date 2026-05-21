/**@odoo-module**/

import {PivotRenderer} from "@web/views/pivot/pivot_renderer";
import {DropdownItemCustomMeasure} from '@web_pivot_computed_measure/dropdown_item_custom_measure/dropdown_item_custom_measure.esm';
const { patch } = require("@web/core/utils/patch");

patch(PivotRenderer.prototype,"web_pivot_computed_measure.PivotRenderer",{
    getFormattedValue(cell) {
        if (cell.value === Infinity) {
            return "-";
        }
        return this._super(...arguments);
    },
});

PivotRenderer.components.DropdownItemCustomMeasure = DropdownItemCustomMeasure
