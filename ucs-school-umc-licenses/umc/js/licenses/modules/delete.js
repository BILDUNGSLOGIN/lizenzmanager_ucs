define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  '../common/Module',
    './delete/SearchPage'
], function(declare, lang, Module, SearchPage) {
  return declare('umc.modules.licenses.delete', [Module], {

    openDetailPage: function() {

    },

    buildRendering: function() {
      this.inherited(arguments);

      const searchPage = new SearchPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
        openDetailPage: lang.hitch(this, 'openDetailPage'),
      });

      this.addPage(searchPage);
    },
  });
});