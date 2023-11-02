/*
 * Copyright 2023 Univention GmbH
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
  'dojo/dom',
  'dojo/dom-class',
  'dojo/aspect',
  'dojo/on',
  'dojo/mouse',
  'dojo/query',
  'dojo/date/locale',
  'dojox/html/entities',
  'dijit/Tooltip',
  'umc/store',
  'umc/tools',
  '../../common/Page',
  'umc/widgets/Grid',
  'umc/widgets/Form',
  'umc/widgets/SearchForm',
  'umc/widgets/TextBox',
  'umc/widgets/DateBox',
  'umc/widgets/ComboBox',
  'umc/widgets/CheckBox',
  'umc/widgets/SuggestionBox',
  'umc/widgets/Text',
  'put-selector/put',
  '../../common/ProductColumns',
  'umc/i18n!umc/modules/licenses',
  '../../../libraries/FileHelper',
  '../../../libraries/base64',
], function(
    declare,
    lang,
    dom,
    domClass,
    aspect,
    on,
    mouse,
    query,
    dateLocale,
    entities,
    Tooltip,
    store,
    tools,
    Page,
    Grid,
    Form,
    SearchForm,
    TextBox,
    DateBox,
    ComboBox,
    CheckBox,
    SuggestionBox,
    Text,
    put,
    ProductColumns,
    _,
) {
  return declare('umc.modules.licenses.users.SearchPage',
      [Page, ProductColumns], {
        //// overwrites
        fullWidth: true,

        //// self
        standbyDuring: null, // required parameter
        moduleFlavor: null, // required parameter
        getSchoolId: function() {
        }, // required parameter
        showChangeSchoolButton: false,
        activeCover: [],

        _grid: null,
        _gridGroup: null,
        _excelExportForm: null,
        _searchForm: null,

        maxUserSum: '-',
        assignedSum: '-',
        expiredSum: '-',
        availableSum: '-',
        userCount: null,

        query: function() {
          this.standbyDuring(
              this._searchForm.ready().then(
                  lang.hitch(this, function() {
                    this._searchForm.submit();
                  }),
              ),
          );
        },

        afterPageChange: function() {
          if (this._grid) {
            this._grid.resize();
          }
        },

        refreshGrid: function(values, resize = false) {
          values.school = this.getSchoolId();
          this._grid.filter(values);
        },

        exportToExcel: function(values) {
          tools.umcpCommand('licenses/users/export_to_excel', values).then(
              lang.hitch(this, function(response) {
                const res = response.result;
                if (res.errorMessage) {
                  dialog.alert(result.errorMessage);
                } else {
                  downloadFile(res.URL, 'license.xlsx');
                }
                this._excelExportForm._buttons.submit.set('disabled', false);
              }),
          );
        },

        createAfterSchoolChoose: function() {
          if (this._searchForm) {
            this.removeChild(this._searchForm);
          }

          if (this._excelExportForm) {
            this.removeChild(this._excelExportForm);
          }

          if (this._grid) {
            this.removeChild(this._grid);
          }

          this._excelExportForm = new Form({
            widgets: [],
            buttons: [
              {
                name: 'submit',
                label: _('Export'),
                style: 'margin-top:20px',
              },
            ],
          });

          this._excelExportForm.on(
              'submit',
              lang.hitch(this, function() {
                values = this._searchForm.value;
                values.school = this.getSchoolId();
                values.pattern = this._searchForm.value.pattern;
                this.exportToExcel(values);
              }),
          );

          const widgets = [
            {
              type: DateBox,
              name: 'import_date_start',
              label: _('Import date start'),
              size: 'TwoThirds',
            },
            {
              type: DateBox,
              name: 'import_date_end',
              label: _('Import date end'),
              size: 'TwoThirds',
            },
            {
              type: SuggestionBox,
              name: 'class_group',
              label: _('Class'),
              staticValues: [{id: '', label: ''}],
              dynamicValues: 'licenses/classes',
              dynamicOptions: {
                school: this.getSchoolId(),
              },
              size: 'TwoThirds',
            },
            {
              type: ComboBox,
              name: 'workgroup',
              label: _('Workgroup'),
              size: 'TwoThirds',
              staticValues: [{id: '', label: ''}],
              dynamicValues: 'licenses/workgroups',
              dynamicOptions: {
                school: this.getSchoolId(),
              },
            },
            {
              type: TextBox,
              name: 'username',
              label: _('Username'),
              size: 'TwoThirds',
            },
            {
              type: TextBox,
              name: 'medium',
              label: _('Media Title'),
              size: 'TwoThirds',
            },
            {
              type: TextBox,
              name: 'medium_id',
              label: _('Medium ID'),
              size: 'TwoThirds',
            },
            {
              type: ComboBox,
              name: 'publisher',
              label: _('Publisher'),
              size: 'TwoThirds',
              staticValues: [{id: '', label: ''}],
              dynamicValues: 'licenses/publishers',
              dynamicOptions: {
                school: this.getSchoolId(),
              },
            },
            {
              type: ComboBox,
              name: 'validStatus',
              label: _('Validity status'),
              staticValues: [
                {
                  id: '', label: '',
                },
                {
                  id: '-', label: _('unknown'),
                },
                {
                  id: '0', label: _('invalid'),
                }, {
                  id: '1', label: _('valid'),
                }],
              size: 'TwoThirds',
            },
            {
              type: ComboBox,
              name: 'usageStatus',
              label: _('Usage status'),
              staticValues: [
                {
                  id: '', label: '',
                },
                {
                  id: '-', label: _('unknown'),
                },
                {
                  id: '0', label: _('not activated'),
                }, {
                  id: '1', label: _('activated'),
                }],
              size: 'TwoThirds',
            },
            {
              type: CheckBox,
              name: 'notProvisioned',
              label: _('Only assigned, not yet provisioned licenses'),
              size: 'TwoThirds',
            },
          ];
          this._searchForm = new SearchForm({
            class: 'umcUDMSearchForm umcUDMSearchFormSimpleTextBox',
            region: 'nav',
            widgets: widgets,
            layout: [
              ['import_date_start', 'import_date_end'],
              ['class_group', 'workgroup'],
              ['medium', 'medium_id', 'publisher'],
              ['validStatus', 'usageStatus', 'notProvisioned'],
              ['username', 'submit'],
            ],
            onSearch: lang.hitch(this, function(values) {
              this.refreshGrid(values, true);
            }),
          });

          const actions = [];

          this._grid = new Grid({
            actions: actions,
            columns: [
              {
                name: 'uid',
                label: _('Username'),
                width: '175px',
              },
              {
                name: 'license',
                label: _('LC'),
                width: '35px',
              },
              {
                name: 'medium',
                label: _('Medium'),
              },
              {
                name: 'classes',
                label: _('Classes'),
                width: '90px',
              },
              {
                name: 'workgroups',
                label: _('Workgroups'),
                width: '90px',
              },
              {
                name: 'roles',
                label: _('Role'),
                width: '20px',
              },
              {
                name: 'publisher',
                label: _('Publisher'),
                width: '35px',
              },
              {
                name: 'date_assignment',
                label: _('Date of assignment'),
                width: '90px',
              },
              {
                name: 'import_date',
                label: _('Import date'),
                width: '90px',

              },
            ],
            moduleStore: store('assignment', 'licenses/users/list'),
            sortIndex: -1,
            addTitleOnCellHoverIfOverflow: true,
          });

          this.addChild(this._searchForm);
          this.addChild(this._excelExportForm);
          this.addChild(this._grid);
        },

        buildRendering: function() {
          this.inherited(arguments);
        },
      });
});
