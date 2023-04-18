define([
  'dojo/_base/declare',
  'umc/widgets/Module',
  'umc/widgets/Text',

], function(declare, Module, Text) {
  return declare('umc.modules.licenses.licenses', [Module], {

    buildRendering: function() {
      this.inherited(arguments);
      this._text = new Text({content: 'licenses'});
      this.addChild(this._text);
    },
  });
});