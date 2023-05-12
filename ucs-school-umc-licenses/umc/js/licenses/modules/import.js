define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  '../common/Module',
    './import/import'
], function(declare, lang, Module, ImportPage) {
  return declare('umc.modules.licenses.import', [Module], {

    buildRendering: function() {
      this.inherited(arguments);
      this.importPage = new ImportPage({
        'getSchoolId': lang.hitch(this, 'getSchoolId')
      });

      this.addPage(this.importPage);
    },
  });
});