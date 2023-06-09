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
  'dojo/dom',
  'dojo/dom-class',
  'dojo/on',
  'dojo/date/locale',
  'dojo/Deferred',
  'dojox/html/entities',
  'dijit/Tooltip',
  'umc/dialog',
  'umc/store',
  'umc/tools',
  '../../common/Page',
  'umc/widgets/Grid',
  'umc/widgets/Form',
  'umc/widgets/Text',
  'umc/widgets/ProgressInfo',
  '../../common/LicenseSearchformMixin',
  '../../common/FormatterMixin',
  'umc/i18n!umc/modules/licenses',
  '../../../libraries/FileHelper',
  '../../../libraries/base64',
], function(
    declare,
    lang,
    dom,
    domClass,
    on,
    dateLocale,
    Deferred,
    entities,
    Tooltip,
    dialog,
    store,
    tools,
    Page,
    Grid,
    Form,
    Text,
    ProgressInfo,
    LicenseSearchformMixin,
    FormatterMixin,
    _,
) {
  return declare('umc.modules.licenses.license.SearchPage',
      [Page, LicenseSearchformMixin, FormatterMixin], {
        //// overwrites
        fullWidth: true,

        //// self
        standbyDuring: null, // required parameter
        getSchoolId: function() {}, // required parameter
        showChangeSchoolButton: false,

        _licenseTypes: [], // reference to the currently active grid
        _grid: null,
        _gridFooter: null,
        _gridOverview: null,
        _gridGroup: null,
        _excelExportForm: null,
        _searchForm: null,

        _isAdvancedSearch: false,

        maxUserSum: '-',
        assignedSum: '-',
        expiredSum: '-',
        availableSum: '-',

        query: function() {
          this.standbyDuring(// Deactivated in this flavor due to Issue #97
              this._searchForm.ready().then(lang.hitch(this, function() {
                this._searchForm.submit();
              })));
        },

        onChangeUsers: function() {
          this.resetAdvancedSearch();
        },

        onChangeProduct: function() {
          this.resetAdvancedSearch();
        },

        resetAdvancedSearch: function() {
          if (this._isAdvancedSearch) {
            this._toggleSearch();
          }
        },

        refreshGrid: function(values) {
          values.school = this.getSchoolId();
          values.isAdvancedSearch = true;

          if (values.licenseType == '') {
            values.licenseType = [];
          } else if (values.licenseType == 'SINGLE') {
            values.licenseType = ['SINGLE'];
          } else if (values.licenseType == 'VOLUME') {
            values.licenseType = ['VOLUME'];
          } else if (values.licenseType == 'SCHOOL') {
            values.licenseType = ['SCHOOL'];
          } else if (values.licenseType == 'WORKGROUP') {
            values.licenseType = ['WORKGROUP'];
          }
          this._grid.filter(values);
          values.licenseType = '';
        },

        saveData: (function (data, fileName) {
          var a = document.createElement("a");
          document.body.appendChild(a);
          a.style = "display: none";
          return function (data, fileName) {
              var json = JSON.stringify(data),
                  blob = new Blob([json], {type: "octet/stream"}),
                  url = window.URL.createObjectURL(blob);
              a.href = url;
              a.download = fileName;
              a.click();
              window.URL.revokeObjectURL(url);
          }}
        ),
        

        exportToExcel: function(values) {
          tools.umcpCommand('licenses/export_to_excel', values).then(
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
        },// allow only either class or workgroup to be set

        //// lifecycle
        postMixInProperties: function() {
          this.inherited(arguments);
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
                this._excelExportForm._buttons.submit.set('disabled', true);
                values = this._searchForm.value;
                values.isAdvancedSearch = this._isAdvancedSearch;
                values.onlyAvailableLicenses = false;
                values.school = this.getSchoolId();


                if (values.licenseType == '') {
                  values.licenseType = [];
                } else if (values.licenseType == 'SINGLE') {
                  values.licenseType = ['SINGLE'];
                } else if (values.licenseType == 'VOLUME') {
                  values.licenseType = ['VOLUME'];
                } else if (values.licenseType == 'SCHOOL') {
                  values.licenseType = ['SCHOOL'];
                } else if (values.licenseType == 'WORKGROUP') {
                  values.licenseType = ['WORKGROUP'];
                }

                this.exportToExcel(values);
              }),
          );

          const actions = [];
          actions.push({
            name: 'edit',
            label: _('Edit'),
            iconClass: 'umcIconEdit',
            isStandardAction: true,
            isContextAction: true,
            isMultiAction: false,
            callback: lang.hitch(this, function(_idxs, licenses) {
              this.openDetailPage(licenses[0].licenseCode);
            }),
          });
          const columnsOverview = [
            {
              name: 'licenseCode', label: _('License code'), width: '66px',
              formatter: lang.hitch(this, 'formatInvalid')
            }, {
              name: 'productId',
              label: _('Medium ID'),
              width: '66px',
              formatter: lang.hitch(this, function(value, license) {
                if (value && value.startsWith('urn:bilo:medium:')) {
                  value = value.slice(16, value.length);
                }
                return value;
              }),
            }, {
              name: 'productName', label: _('Medium'), width: '200px',
            }, {
              name: 'publisher', label: _('Publisher'), width: '50px',
            }, {
              name: 'licenseTypeLabel', label: _('License type'), width: '66px',
            }, {
              name: 'for', label: _('For'), width: '66px',
            }, {
              name: 'countAquired', label: _('Max. Users'), width: '66px',
            }, {
              name: 'countAssigned', label: _('Assigned'), width: '66px',
              formatter: lang.hitch(this, 'formatActivated')
            }, {
              name: 'countExpired', label: _('Expired'), width: '66px',
            }, {
              name: 'countAvailable', label: _('Available'), width: '66px',
            }, {
              name: 'importDate',
              label: _('Delivery'),
              width: '66px',
              formatter: lang.hitch(this, function(value, license) {
                if (value) {
                  value = dateLocale.format(new Date(value), {
                    fullYear: true, selector: 'date',
                  });
                }
                return value;
              }),
            }];

          this._grid = new Grid({
            actions: actions,
            columns: columnsOverview,
            moduleStore: store('licenseCode', 'licenses'),
            sortIndex: -10,
            addTitleOnCellHoverIfOverflow: true,
            class: 'licensesTable__licenses',
            gridOptions: {
              selectionMode: 'single',
            },
            selectorType: 'radio',
          });

          this.createLicenseSearchWidget();

          this.addChild(this._searchForm);
          this.addChild(this._excelExportForm);
          this.addChild(this._grid);
        },

        buildRendering: function() {
          this.inherited(arguments);
          this._isAdvancedSearch = true;

          // retrieve chunksize from UCR if present.
          tools.ucr('bildungslogin/assignment/chunksize').
              then(lang.hitch(this, function(data) {
                this.allocation_chunksize = data['bildungslogin/assignment/chunksize'];
              }));
        },
      });
});
