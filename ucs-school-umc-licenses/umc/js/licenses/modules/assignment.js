define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  '../common/Module',
  './assignment/UserSelectionPage',
  './assignment/ProductSearchPage',
  './assignment/LicenseSearchPage',
  'umc/i18n!umc/modules/licenses',
], function(
    declare,
    lang,
    Module,
    UserSelectionPage,
    ProductSearchPage,
    LicenseSearchPage,
    _) {
  return declare('umc.modules.licenses.assignment', [Module], {
    userIds: [],
    productId: null,
    group: null,
    groupName: null,
    userCount: null,
    _assignmentType: null,

    setUserIds: function(userIds) {
      this.userIds = userIds;
      this.setAssignmentType('user');
      this._headerButtons.toChangeUser.set('visible', true);
      this.nextPage();
    },

    setGroup: function(group, groupName, type) {
      this.setAssignmentType(type);
      this.group = group;
      this.groupName = groupName;
      this._headerButtons.toChangeUser.set('visible', true);
      this.nextPage();
    },

    setSchoolAssignment: function() {
      this.setAssignmentType('school');
      this._headerButtons.toChangeUser.set('visible', true);
      this.selectPage(3);
    },

    getGroup: function() {
      return this.group;
    },

    getGroupName: function() {
      return this.groupName;
    },

    setProductId: function(productId) {
      this.productId = productId;
      this._headerButtons.changeMedium.set('visible', true);
      this.nextPage();
      this.currentPage().updateText();
    },

    setAssignmentType: function(type) {
      allowed_types = ['user', 'schoolClass', 'workgroup', 'school'];

      if (allowed_types.includes(type)) {
        this._assignmentType = type;
      } else {
        console.error('Assignment type needs to be one of: ', allowed_types);
      }
    },

    getAssignmentType: function() {
      return this._assignmentType;
    },

    getUserIds: function() {
      return this.userIds;
    },

    getProductId: function() {
      return this.productId;
    },

    toChangeUser: function() {
      this._headerButtons.toChangeUser.set('visible', false);
      this._headerButtons.changeMedium.set('visible', false);
      this.selectPage(1);
    },

    setUserCount: function(userCount) {
      this.userCount = userCount;
    },

    getUserCount: function() {
      return this.userCount
    },

    backToChooseSchool: function() {
      this.inherited(arguments);
      this._headerButtons.toChangeUser.set('visible', false);
      this._headerButtons.changeMedium.set('visible', false);
    },

    backToChooseProduct: function() {
      this._headerButtons.changeMedium.set('visible', false);
      this.selectPage(2);
    },

    postMixInProperties: function() {
      this.inherited(arguments);

      this.addHeaderButton({
        name: 'toChangeUser',
        label: _('Change user selection'),
        callback: lang.hitch(this, 'toChangeUser'),
        visible: false,
      });

      this.addHeaderButton({
        name: 'changeMedium',
        label: _('Change medium'),
        callback: lang.hitch(this, 'backToChooseProduct'),
        visible: false,
      });
    },

    buildRendering: function() {
      this.inherited(arguments);

      this.userIds = [];
      this.productId = null;
      this.group = null;
      this._assignmentType = null;

      const userSelectionPage = new UserSelectionPage({
        'setHeaderButtons': lang.hitch(this, 'setHeaderButtons'),
        'getMultipleSchools': lang.hitch(this, 'getMultipleSchools'),
        'backToChooseSchool': lang.hitch(this, 'backToChooseSchool'),
        'getSchoolId': lang.hitch(this, 'getSchoolId'),
        'setUserIds': lang.hitch(this, 'setUserIds'),
        'setGroup': lang.hitch(this, 'setGroup'),
        'setSchoolAssignment': lang.hitch(this, 'setSchoolAssignment'),
      });
      const productSearchPage = new ProductSearchPage({
        'getSchoolId': lang.hitch(this, 'getSchoolId'),
        'getUserIds': lang.hitch(this, 'getUserIds'),
        'setProductId': lang.hitch(this, 'setProductId'),
        'getAssignmentType': lang.hitch(this, 'getAssignmentType'),
        'getGroup': lang.hitch(this, 'getGroup'),
        'getGroupName': lang.hitch(this, 'getGroupName'),
        'setUserCount': lang.hitch(this, 'setUserCount')
      });
      const licenseSearchPage = new LicenseSearchPage({
        'getSchoolId': lang.hitch(this, 'getSchoolId'),
        'getUserIds': lang.hitch(this, 'getUserIds'),
        'getProductId': lang.hitch(this, 'getProductId'),
        'getAssignmentType': lang.hitch(this, 'getAssignmentType'),
        'standbyDuring': lang.hitch(this, 'standbyDuring'),
        'getGroup': lang.hitch(this, 'getGroup'),
        'getGroupName': lang.hitch(this, 'getGroupName'),
        'getUserCount': lang.hitch(this, 'getUserCount'),
      });

      this.addPage(userSelectionPage);
      this.addPage(productSearchPage);
      this.addPage(licenseSearchPage);

    },
  });
});