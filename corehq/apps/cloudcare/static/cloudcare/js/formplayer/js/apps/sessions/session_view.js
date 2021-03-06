/*global FormplayerFrontend */

FormplayerFrontend.module("SessionNavigate.SessionList", function (SessionList, FormplayerFrontend, Backbone, Marionette) {
    SessionList.SessionView = Marionette.ItemView.extend({
        tagName: "tr",

        events: {
            "click": "rowClick",
        },

        template: "#session-view-item-template",

        rowClick: function (e) {
            e.preventDefault();
            var model = this.model;
            FormplayerFrontend.trigger("getIncompleteForm", model.get('sessionId'));
        },
    });

    SessionList.SessionListView = Marionette.CompositeView.extend({
        tagName: "div",
        template: "#session-view-list-template",
        childView: SessionList.SessionView,
        childViewContainer: "tbody",
    });
});