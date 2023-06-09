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
      this._headerButtons.save.set('visible', true);
      this._headerButtons.backToOverview.set('visible', true);
    },

    afterChooseSchool: function() {
      this.searchPage.createAfterSchoolChoose();
      if (this.state.license && this.state.license[0] !== '') {
        this.openDetailPage(this.state.license[0]);
      }
    },

    backToOverview: function() {
      this.selectPage(1);
      this.deleteState('license');
      this._headerButtons.save.set('visible', false);
      this._headerButtons.save.set('disabled', true);
      this._headerButtons.backToOverview.set('visible', false);
    },

    getSaveButton: function() {
      return this._headerButtons.save;
    },

    postMixInProperties: function() {
      this.inherited(arguments);

      this.addHeaderButton({
        name: 'save',
        label: _('Save'),
        callback: lang.hitch(this, function() {
          this.detailPage.save();
        }),
        visible: false,
        disabled: true,
      });
      this.addHeaderButton({
        name: 'backToOverview',
        label: _('To license overview'),
        callback: lang.hitch(this, 'backToOverview'),
        visible: false,
      });
    },

    buildRendering: function() {
      this.inherited(arguments);
      this.searchPage = new SearchPage({
        getSchoolId: lang.hitch(this, 'getSchoolId'),
        openDetailPage: lang.hitch(this, 'openDetailPage'),
      });
      this.addPage(this.searchPage);

      this.detailPage = new DetailPage({
        standbyDuring: lang.hitch(this, 'standbyDuring'),
        onBack: lang.hitch(this, 'backToOverview'),
        getSaveButton: lang.hitch(this, 'getSaveButton'),
      });
      this.addPage(this.detailPage);
    },
  });
});