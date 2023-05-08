define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojox/html/entities',
  'umc/widgets/Text',
  '../common/Module',
  './products/SearchPage',
  './products/DetailPage',
  'umc/i18n!umc/modules/licenses',
], function(declare, lang, entities, Text, Module, SearchPage, DetailPage, _) {
  return declare('umc.modules.licenses.products', [Module], {
    searchPage: null,
    pages: [],

    openDetailPage: function(productId) {
      this.updateState('product', [productId]);
      this.selectPage(2);
      this.currentPage().load(productId);
      this._headerButtons.backToOverview.set('visible', true);
    },

    afterChooseSchool: function() {
      if (this.state.product && this.state.product[0] !== '') {
        this.openDetailPage(this.state.product[0]);
      }
    },

    backToOverview: function() {
      this._headerButtons.backToOverview.set('visible', false);
      this.selectPage(1);
      this.deleteState('product');
    },

    postMixInProperties: function () {
      this.inherited(arguments);
      this.addHeaderButton({
        name: 'backToOverview',
        label: _('Back to media overview'),
        callback: lang.hitch(this, 'backToOverview'),
        visible: false,
      });
    },

    buildRendering: function() {
      this.inherited(arguments);

      const searchPage = new SearchPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
        openDetailPage: lang.hitch(this, 'openDetailPage'),
      });
      this.addPage(searchPage);

      const detailPage = new DetailPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
        standbyDuring: lang.hitch(this, 'standbyDuring'),
      });
      this.addPage(detailPage);
    },
  });
});