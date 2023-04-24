define([
  'dojo/_base/declare',
  '../common/Module',
    './import/import'
], function(declare, Module, ImportPage) {
  return declare('umc.modules.licenses.import', [Module], {

    buildRendering: function() {
      this.inherited(arguments);
      this.importPage = new ImportPage();

      this.addPage(this.importPage);
    },
  });
});