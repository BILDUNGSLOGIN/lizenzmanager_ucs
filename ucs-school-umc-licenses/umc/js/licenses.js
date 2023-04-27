/*
 * Copyright 2021 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define*/

define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojo/on',
  'dojox/html/entities',
  'umc/widgets/Module',
  'umc/widgets/Text',
  './licenses/common/ChooseSchoolPage',
  './licenses/modules/assignment',
  './licenses/modules/import',
  './licenses/modules/licenses',
  './licenses/modules/products',
  './licenses/LicenseDetailPage',
  './licenses/LicenseSearchPage',
  './licenses/ProductDetailPage',
  './licenses/ProductSearchPage',
  './licenses/UserSelectionPage',
  './licenses/ImportMediaLicensePage',
  'umc/i18n!umc/modules/licenses',
  'xstyle/css!./licenses.css',
], function(
    declare,
    lang,
    on,
    entities,
    Module,
    Text,
    ChooseSchoolPage,
    AssignmentModule,
    ImportModule,
    LicensesModule,
    ProductsModule,
    LicenseDetailPage,
    LicenseSearchPage,
    ProductDetailPage,
    ProductSearchPage,
    UserSelectionPage,
    ImportMediaLicensePage,
    _,
) {
  return declare('umc.modules.licenses', [Module], {
    _schoolLabelWidget: null,
    schoolLabel: '&nbsp;',

    updateModuleState: function(state) {
      this.set('moduleState', state);
    },

    onClose: function() {
      this.inherited(arguments);
      this.module.close();
      return true;
    },


    setSchoolLabel: function(schoolLabel) {
      this.set(
          'schoolLabel',
          _('for %(school)s', {
            school: entities.encode(schoolLabel),
          }),
      );
    },

    _setSchoolLabelAttr: function(schoolLabel) {
      if (!this._schoolLabelWidget) {
        this._schoolLabelWidget = new Text({
          content: '',
        });
        // FIXME(?) usage of private inherited variables
        this._top._left.addChild(this._schoolLabelWidget);
      }
      this._schoolLabelWidget.set('content', schoolLabel);
      this._set('schoolLabel', schoolLabel);
    },

    resetView: function() {
      this.selectChild(this.module);
    },

    //// lifecycle
    buildRendering: function() {
      this.inherited(arguments);

      const props = {
        moduleState: this.moduleState,
        resetView: lang.hitch(this, 'resetView'),
        updateModuleState: lang.hitch(this, 'updateModuleState'),
        setSchoolLabel: lang.hitch(this, 'setSchoolLabel'),
      };

      switch (this.moduleFlavor) {
        case 'licenses/allocation':
          this.module = new AssignmentModule(props);
          break;
        case 'licenses/licenses':
          this.module = new LicensesModule(props);
          break;
        case 'licenses/products':
          this.module = new ProductsModule(props);
          break;
        case 'licenses/import':
          this.module = new ImportModule(props);
          break;
      }

      this.addChild(this.module);
    },
  });
});
