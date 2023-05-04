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
    _assignmentType: null,

    setUserIds: function(userIds) {
      this.userIds = userIds;
      this.setAssignmentType('user');
      this.updateState('user', userIds);
      this._headerButtons.toChangeUser.set('visible', true);
      this.nextPage();
    },

    setGroup: function(group, type) {
      this.setAssignmentType(type);
      this.group = group;
      this.updateState('type', [type]);
      this.updateState('group', [group]);
      this._headerButtons.toChangeUser.set('visible', true);
      this.nextPage();
    },

    setSchoolAssignment: function() {
      this.setAssignmentType('school');
      this.updateState('type', ['school']);
      this._headerButtons.toChangeUser.set('visible', true);
      this.selectPage(3);
    },

    getGroup: function() {
      return this.group;
    },

    setProductId: function(productId) {
      this.productId = productId;
      this.updateState('product', [productId]);
      this._headerButtons.changeMedium.set('visible', true);
      this.nextPage();
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
      if (this.state.product) {
        this.deleteState('product');
      }

      if (this.state.user) {
        this.deleteState('user');
      }

      if (this.state.group) {
        this.deleteState('group');
      }

      this._headerButtons.toChangeUser.set('visible', false);
      this._headerButtons.changeMedium.set('visible', false);
      this.selectPage(1);
    },

    backToChooseSchool: function() {
      this.inherited(arguments);
      this._headerButtons.toChangeUser.set('visible', false);
      this._headerButtons.changeMedium.set('visible', false);
    },

    backToChooseProduct: function() {
      if (this.state.product) {
        this.deleteState('product');
      }
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

    afterChooseSchool: function() {
      if (this.state.user && this.state.user[0] !== '') {
        this.setUserIds(this.state.user);
      }

      if (this.state.type && this.state.type[0] === 'school') {
        this.setSchoolAssignment();
      }

      if (this.state.type && this.state.type[0] !== 'school' && this.state.group[0] !== '') {
        this.setGroup(this.state.group[0], this.state.type[0]);
      }

      if (this.state.product && this.state.product[0] !== '') {
        this.setProductId(this.state.product[0]);
      }
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
      });
      const licenseSearchPage = new LicenseSearchPage({
        'getSchoolId': lang.hitch(this, 'getSchoolId'),
        'getUserIds': lang.hitch(this, 'getUserIds'),
        'getProductId': lang.hitch(this, 'getProductId'),
        'getAssignmentType': lang.hitch(this, 'getAssignmentType'),
        'standbyDuring': lang.hitch(this, 'standbyDuring'),
      });

      this.addPage(userSelectionPage);
      this.addPage(productSearchPage);
      this.addPage(licenseSearchPage);

    },
  });
});