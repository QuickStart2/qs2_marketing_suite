# Copyright 2020 Tecnativa - Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
{
    "name": "Web Pivot Computed Measure",
    "category": "web",
    "version": "19.0.1.0.0",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "auto_install": False,
    "installable": True,
    "maintainers": ["CarlosRoca13"],
    "demo": [
        "demo/demo_users_pivot_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_pivot_computed_measure/static/src/helpers/utils.esm.js",
            "web_pivot_computed_measure/static/src/dropdown_item_custom_measure/dropdown_item_custom_measure.esm.js",
            "web_pivot_computed_measure/static/src/report_view_measures/report_view_measures.esm.js",
            "web_pivot_computed_measure/static/src/pivot/pivot_controller.esm.js",
            "web_pivot_computed_measure/static/src/pivot/pivot_model.esm.js",
            "web_pivot_computed_measure/static/src/pivot/pivot_renderer.esm.js",
            "web_pivot_computed_measure/static/src/dropdown_item_custom_measure/dropdown_item_custom_measure.scss",
            "web_pivot_computed_measure/static/src/dropdown_item_custom_measure/dropdown_item_custom_measure.xml",
            "web_pivot_computed_measure/static/src/report_view_measures/report_view_measures.xml",
            "web_pivot_computed_measure/static/src/pivot/pivot_view.xml",
        ],
        "web.assets_tests": [
            "web_pivot_computed_measure/static/src/test/test.esm.js",
        ],
    },
}
