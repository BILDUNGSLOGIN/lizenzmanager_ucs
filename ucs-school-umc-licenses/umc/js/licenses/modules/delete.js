define([
  'dojo/_base/declare',
  '../common/Module',
], function(declare, Module) {
  return declare('umc.modules.licenses.delete', [Module], {

    buildRendering: function() {
      this.inherited(arguments);
    },
  });
});