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
      this.selectPage(2);
      this.currentPage().load(this.getSchoolId(), licenseId);
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

    // buildRendering: function() {
    //   this.inherited(arguments);
    //   this._text = new Text({content: 'licenses'});
    //   this.addChild(this._text);
    // },
  });
});