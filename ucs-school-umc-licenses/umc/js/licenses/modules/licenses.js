define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojox/html/entities',
  'umc/widgets/Text',
  '../common/Module',
  './licenses/SearchPage',
  './licenses/DetailPage',
  'umc/i18n!umc/modules/licenses',
], function(declare, lang, entities, Text, Module, SearchPage, DetailPage, _) {
  return declare('umc.modules.licenses.licenses', [Module], {

    searchPage: null,
    pages: [],

    openDetailPage: function(licenseId) {
      this.updateState('license', [licenseId]);
      this.selectPage(2);
      this.currentPage().load(licenseId);
    },

    afterChooseSchool: function() {
      if (this.state.license && this.state.license[0] !== '') {
        this.openDetailPage(this.state.license[0]);
      }
    },

    buildRendering: function() {
      this.inherited(arguments);
      const searchPage = new SearchPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
        openDetailPage: lang.hitch(this, 'openDetailPage'),
      });
      this.addPage(searchPage);

      const detailPage = new DetailPage({
        standbyDuring: lang.hitch(this, 'standbyDuring')
      });
      this.addPage(detailPage);
    },
  });
});