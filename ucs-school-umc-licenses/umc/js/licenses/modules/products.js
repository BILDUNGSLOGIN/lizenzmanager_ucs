define([
    "dojo/_base/declare",
    "umc/widgets/Module",
    "umc/widgets/Text"

], function (declare, Module, Text) {
    return declare("umc.modules.licenses.products", [Module], {
        _text: new Text({content: "products"}),

        buildRendering: function () {
            this.inherited(arguments);
            this.addChild(this._text);
            this.selectChild(this._text);
        }
    })
})