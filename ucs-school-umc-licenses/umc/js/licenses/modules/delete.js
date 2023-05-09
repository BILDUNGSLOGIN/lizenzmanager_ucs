define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  '../common/Module',
  './delete/SearchPage',
  './licenses/DetailPage',
  'umc/i18n!umc/modules/licenses'
], function(declare, lang, Module, SearchPage, DetailPage, _) {
  return declare('umc.modules.licenses.delete', [Module], {

    openDetailPage: function(licenseId) {
      this.updateState('license', [licenseId]);
      this.selectPage(2);
      this.currentPage().load(licenseId);
      this._headerButtons.toOverview.set('visible', true);
    },

    backToOverview: function() {
      this.deleteState('license');
      this.selectPage(1);
      this._headerButtons.toOverview.set('visible', false);
    },

    postMixInProperties: function() {
      this.inherited(arguments);

      this.addHeaderButton({
        name: 'toOverview',
        label: _('Back'),
        callback: lang.hitch(this, 'backToOverview'),
        visible: false,
      });
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

      const detailsPage = new DetailPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
        openDetailPage: lang.hitch(this, 'openDetailPage'),
        standbyDuring: lang.hitch(this, 'standbyDuring'),
      });

      this.addPage(searchPage);
      this.addPage(detailsPage);
    },
  });
});