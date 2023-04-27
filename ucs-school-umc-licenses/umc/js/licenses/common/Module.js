define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojox/html/entities',
  'umc/widgets/ContainerWidget',
  'umc/widgets/StandbyMixin',
  'dijit/layout/StackContainer',
  './ChooseSchoolPage',
  'umc/i18n!umc/modules/licenses',
], function(declare, lang, entities, Page, StandbyMixin, StackContainer,
    ChooseSchoolPage, _) {
  return declare('umc.modules.licenses.module', [Page, StandbyMixin], {
    school: '',
    _pages: [],
    _currentPageId: 0,
    multipleSchools: false,
    state: {},
    headerButtons: [],

    //required
    updateModuleState: function(state) {},

    getSchoolId: function() {
      return this.school.id;
    },

    getSchool: function() {
      return this.school;
    },

    getMultipleSchools: function() {
      return this.multipleSchools;
    },

    afterChooseSchool: function() {},

    chooseSchool: function(school, hasMultiple) {
      this.school = school;
      this.multipleSchools = hasMultiple;
      this.setSchoolLabel(school.label);
      this.nextPage();
      this.updateState('school', [school.id]);
      this._headerButtons.changeSchool.set('visible', true);
      this.afterChooseSchool();
    },

    addPage: function(page) {
      this._pages.push(page);
    },

    currentPage: function() {
      return this._pages[this._currentPageId];
    },

    getPageById: function(id) {
      return this._pages[id];
    },

    selectPage: function(page) {
      if (this.currentPage().onPageChange()) {
        this.removeChild(this.currentPage());
        this._currentPageId = page;
        this.addChild(this.getPageById(page));
      }
      this.currentPage().afterPageChange();
      this.resetView();
    },

    nextPage: function() {
      this.selectPage(this._currentPageId + 1);
    },

    close: function() {
      this.removeChild(this.currentPage());
    },

    loadState: function() {
      let state = this.moduleState.split(':');
      while (state.length > 1) {
        this.state[state.shift()] = state.shift().
            replaceAll('+', ':').
            split(',');
      }
    },

    _updateState: function() {
      let state = [];

      for (const key in this.state) {
        state.push(key);
        state.push(this.state[key].map(function(element) {
          return element.replaceAll(':', '+');
        }).join(','));
      }

      this.updateModuleState(state.join(':'));
    },

    updateState: function(key, values) {
      this.state[key] = values;
      this._updateState();
    },

    deleteState: function(key) {
      delete this.state[key];
      this._updateState();
    },

    resetState: function() {
      this.state = [];
      this.updateModuleState('');
    },

    setHeaderButtons: function(headerButtons) {
      this.headerButtons = headerButtons;
    },

    addHeaderButton: function(headerButton) {
      this.headerButtons.push(headerButton);
    },

    backToChooseSchool: function() {
      this.resetState();
      this._headerButtons.changeSchool.set('visible', false);
      this.selectPage(0);
    },

    postMixInProperties: function() {
      this.inherited(arguments);

      this.setHeaderButtons([
        {
          name: 'changeSchool',
          label: _('Change school'),
          callback: lang.hitch(this, 'backToChooseSchool'),
          visible: false,
        },
      ]);
    },

    buildRendering: function() {
      this.inherited(arguments);
      this.school = '';
      this._currentPageId = 0;
      this.multipleSchools = false;
      this._pages = [];
      this.state = {};

      this.loadState();

      this.chooseSchoolPage = new ChooseSchoolPage({
        standbyDuring: lang.hitch(this, 'standbyDuring'),
        chooseSchool: lang.hitch(this, 'chooseSchool'),
        resetState: lang.hitch(this, 'resetState'),
      });

      this.addPage(this.chooseSchoolPage);
      this.addChild(this._pages[0]);

      if (this.state.school && this.state.school[0] !== '') {
        this.school = this.state.school[0];
        this.chooseSchoolPage.trySelectSchool(this.school);
      }
    },
  });
});