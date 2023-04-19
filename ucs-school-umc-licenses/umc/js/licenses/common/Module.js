define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojox/html/entities',
  'umc/widgets/Page',
  'umc/widgets/StandbyMixin',
  'dijit/layout/StackContainer',
  './ChooseSchoolPage',
  'umc/i18n!umc/modules/licenses',
], function(declare, lang, entities, Page, StandbyMixin, StackContainer,
    ChooseSchoolPage, _) {
  return declare('umc.modules.licenses.module', [Page, StandbyMixin], {
    schoolId: '',
    _pages: [],
    _currentPageId: 0,

    getSchoolId: function() {
      return this.schoolId;
    },

    chooseSchool: function(school, hasMultiple) {
      this.schoolId = school.id;
      this.set(
          'schoolLabel',
          _('for %(school)s', {
            school: entities.encode(school.label),
          }),
      );

      this.nextPage();
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
      this.removeChild(this.currentPage());
      this._currentPageId = page;
      this.addChild(this.getPageById(page));
    },

    nextPage: function() {
      this.selectPage(this._currentPageId + 1);
    },

    buildRendering: function() {
      this.inherited(arguments);
      this.schoolId = '';
      this._currentPageId = 0;

      const chooseSchoolPage = new ChooseSchoolPage({
        standbyDuring: lang.hitch(this, 'standbyDuring'),
        chooseSchool: lang.hitch(this, 'chooseSchool'),
      });

      this.addPage(chooseSchoolPage);
      this.addChild(this._pages[0]);
    },
  });
});