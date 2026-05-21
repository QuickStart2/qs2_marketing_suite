/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.Qs2Tracking = publicWidget.Widget.extend({
    selector: "#wrapwrap",

    start() {
        this._super(...arguments);
        const code = new URLSearchParams(window.location.search).get("track");
        if (code) {
            this._activate(code);
        } else {
            this._logPageview();
        }
        return Promise.resolve();
    },

    _activate(code) {
        fetch("/qs2/activate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: { tracking_code: code, url: window.location.href },
            }),
        }).catch(() => {});
    },

    _logPageview() {
        fetch("/qs2/pageview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: { url: window.location.href },
            }),
        }).catch(() => {});
    },
});

export default publicWidget.registry.Qs2Tracking;
