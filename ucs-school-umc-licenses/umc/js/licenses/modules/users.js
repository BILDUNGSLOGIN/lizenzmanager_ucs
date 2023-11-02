define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojox/html/entities',
  'umc/widgets/Text',
  '../common/Module',
  './users/SearchPage',
  'umc/i18n!umc/modules/licenses',
], function(declare, lang, entities, Text, Module, SearchPage, _) {
  return declare('umc.modules.licenses.users', [Module], {
    searchPage: null,
    pages: [],

    afterChooseSchool: function() {
      this.searchPage.createAfterSchoolChoose();
    },

    buildRendering: function() {
      this.inherited(arguments);

      this.searchPage = new SearchPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
      });
      this.addPage(this.searchPage);
    },
  });
});