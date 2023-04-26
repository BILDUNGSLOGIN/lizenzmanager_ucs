define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  '../common/Module',
  './assignment/UserSelectionPage',
  './assignment/ProductSearchPage',
  './assignment/LicenseSearchPage',
], function(
    declare,
    lang,
    Module,
    UserSelectionPage,
    ProductSearchPage,
    LicenseSearchPage) {
  return declare('umc.modules.licenses.assignment', [Module], {
    userIds: [],
    productId: null,
    group: null,
    _assignmentType: null,

    setUserIds: function(userIds) {
      this.userIds = userIds;
      this.setAssignmentType('user');
      this.updateState('user', userIds);
      this.nextPage();
    },

    setGroup: function(group, type) {
      this.setAssignmentType(type);
      this.group = group;
      this.updateState('type', [type]);
      this.updateState('group', [group]);
      this.nextPage();
    },

    getGroup: function() {
      return this.group
    },

    setProductId: function(productId) {
      this.productId = productId;
      this.updateState('product', [productId]);
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

    afterChooseSchool: function() {
      if (this.state.user && this.state.user[0] !== '') {
        this.setUserIds(this.state.user);
      }

      if (this.state.type && this.state.group[0] !== '') {
        this.setGroup(this.state.group[0], this.state.type[0])
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
        'getSchoolId': lang.hitch(this, 'getSchoolId'),
        'setUserIds': lang.hitch(this, 'setUserIds'),
        'setGroup': lang.hitch(this, 'setGroup'),
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