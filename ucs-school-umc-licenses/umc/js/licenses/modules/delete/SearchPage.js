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
  'umc/widgets/CheckBox',
  'umc/widgets/DateBox',
  'umc/widgets/ComboBox',
  'umc/widgets/SearchForm',
  'umc/widgets/Text',
  'umc/widgets/TextBox',
  'umc/widgets/SuggestionBox',
  'umc/widgets/ProgressInfo',
  'umc/i18n!umc/modules/licenses',
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
    CheckBox,
    DateBox,
    ComboBox,
    SearchForm,
    Text,
    TextBox,
    SuggestionBox,
    ProgressInfo,
    _,
) {
  return declare('umc.modules.licenses.license.SearchPage', [Page], {
    //// overwrites
    fullWidth: true,

    //// self
    standbyDuring: null, // required parameter
    getSchoolId: function() {}, // required parameter

    _licenseTypes: [],
    // reference to the currently active grid
    _grid: null,
    _gridFooter: null,
    _searchForm: null,

    _isAdvancedSearch: false,

    maxUserSum: '-',
    assignedSum: '-',
    expiredSum: '-',
    availableSum: '-',

    deferred: null,
    progressInfo: null,
    max: 0,
    current: 0,

    _toggleSearch: function() {
      this._isAdvancedSearch = !this._isAdvancedSearch;

      [
        'timeFrom',
        'timeTo',
        'onlyAvailableLicenses',
        'publisher',
        'licenseType',
        'userPattern',
        'productId',
        'product',
        'licenseCode',
        'workgroup',
        'class',
      ].forEach(
          lang.hitch(this, function(widgetName) {
            const widget = this._searchForm.getWidget(widgetName);
            if (widget) {
              widget.set('visible', this._isAdvancedSearch);
            }
          }),
      );

      this._searchForm.getWidget('pattern').
          set('visible', !this._isAdvancedSearch);

      // update toggle button
      const button = this._searchForm.getButton('toggleSearch');
      if (this._isAdvancedSearch) {
        button.set('iconClass', 'umcDoubleLeftIcon');
      } else {
        button.set('iconClass', 'umcDoubleRightIcon');
      }
    },

    query: function() {
      this.standbyDuring(
          // Deactivated in this flavor due to Issue #97
          this._searchForm.ready().then(
              lang.hitch(this, function() {
                this._searchForm.submit();
              }),
          ),
      );
    },

    resetAdvancedSearch: function() {
      if (this._isAdvancedSearch) {
        this._toggleSearch();
      }
    },

    refreshGrid: function(values) {
      values.isAdvancedSearch = this._isAdvancedSearch;
      values.school = this.getSchoolId();
      values.isAdvancedSearch = true;
      values.onlyAvailableLicenses = true;

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

    //// lifecycle
    postMixInProperties: function() {
      this.inherited(arguments);

      this._licenseTypes = [
        {id: '', label: ''},
        {id: 'SINGLE', label: _('Single license')},
        {id: 'VOLUME', label: _('Volume license')},
        {
          id: 'WORKGROUP',
          label: _('Workgroup license'),
        },
        {
          id: 'SCHOOL',
          label: _('School license'),
        },
      ];
    },

    _delete: function(licenseCodes) {
      let temp_codes = [];

      while (temp_codes.length < this.allocation_chunksize &&
      licenseCodes.length > 0) {
        temp_codes.push(licenseCodes.pop());
      }

      tools.umcpCommand('licenses/delete', {licenses: temp_codes}).
          then(function(result) {
            this.current += temp_codes.length;

            if (this.progressInfo) {
              this.progressInfo.update(this.current,
                  _('Deleted %s', this.current, this.max));
            }

            if (licenseCodes.length > 0) {
              this._delete(licenseCodes);
            }

          }, function(result) {
            this.deferred.resolve({
              'error': null,
              'message': null,
              'reason': null,
              'result': null,
            });
            this.progressInfo.destroyRecursive();
            alert('something went wrong');
          });
    },

    deleteLicenses: function(licenses) {
      this.deferred = new Deferred();
      let licenseCodes = licenses.map(function(element) {
        return element.licenseCode;
      });

      this.max = licenseCodes.length;
      this.current = 0;

      if (licenseCodes.length <= this.allocation_chunksize) {
        this._delete(licenseCodes);
      } else {
        this.progressInfo = new ProgressInfo({
          maximum: licenseCodes.length,
        });

        this.progressInfo._delete.set('maximum', licenseCodes.length);

        this._delete(licenseCodes);

        this.standbyDuring(this.deferred, this.progressInfo);
      }
    },

    askDeleteLicenses: function(licenses) {
      let count = licenses.length;
      let message = `<p>${_(
          'You have selected %s licenses. ' +
          'Do you really want to delete this? ' +
          'This process is irreversible!',
          count)}</p>`;

      if (count > 1000) {
        message += `<p>${_(
            'You have selected over a thousand licenses for deletion. This process will take several minutes.')}</p>`;
      }

      dialog.confirm(message, [
        {
          'label': _('Cancel'),
        },
        {
          'label': _('Delete'),
          'callback': lang.hitch(this, function() {
            this.deleteLicenses(licenses);
          }),
        },
      ]);
    },

    afterPageChange: function() {
      this.refreshGrid({});
    },

    buildRendering: function() {
      this.inherited(arguments);

      // retrieve chunksize from UCR if present.
      tools.ucr('bildungslogin/assignment/chunksize').
          then(lang.hitch(this, function(data) {
            this.allocation_chunksize = data['bildungslogin/assignment/chunksize'];
          }));

      const widgets = [
        {
          type: DateBox,
          name: 'timeFrom',
          visible: false,
          label: _('Start import period'),
          size: 'TwoThirds',
        },
        {
          type: DateBox,
          name: 'timeTo',
          label: _('End import period'),
          size: 'TwoThirds',
          visible: false,
        },
        {
          type: ComboBox,
          name: 'licenseType',
          label: _('License type'),
          staticValues: this._licenseTypes,
          size: 'TwoThirds',
          visible: false,
        },
        {
          type: TextBox,
          name: 'userPattern',
          label: _('User ID'),
          description: _(
              'Search for licenses that have this user assigned. (Searches for \'first name\', \'last name\' and \'username\')',
          ),
          size: 'TwoThirds',
          visible: false,
        },
        {
          type: TextBox,
          name: 'licenseCode',
          label: _('License code'),
          size: 'TwoThirds',
          visible: false,
        },
        {
          type: TextBox,
          name: 'pattern',
          label: '&nbsp;',
          inlineLabel: _('Search licenses'),
        },
      ];
      const layout = [
        ['timeFrom', 'timeTo', 'onlyAvailableLicenses'],
        ['publisher', 'licenseType', 'userPattern'],
        ['workgroup', 'class'],
        [
          'productId',
          'product',
          'licenseCode',
          'pattern',
          'submit',
          'toggleSearchLabel',
          'toggleSearch',
        ],
      ];
      const buttons = [
        {
          name: 'toggleSearch',
          labelConf: {
            class: 'umcFilters',
          },
          label: _('Filters'),
          iconClass: 'umcDoubleRightIcon',

          callback: lang.hitch(this, function() {
            this._toggleSearch();
          }),
        },
      ];
      this._searchForm = new SearchForm({
        class: 'umcUDMSearchForm umcUDMSearchFormSimpleTextBox',
        region: 'nav',
        widgets: widgets,
        buttons: buttons,
        layout: layout,
        onSearch: lang.hitch(this, function(values) {
          this.refreshGrid(values);
        }),
      });
      domClass.add(
          this._searchForm.getWidget('licenseCode').$refLabel$.domNode,
          'umcSearchFormElementBeforeSubmitButton',
      );

      const actions = [];
      actions.push({
        name: 'delete',
        label: _('Delete'),
        iconClass: 'trash',
        isStandardAction: true,
        isContextAction: true,
        isMultiAction: true,
        callback: lang.hitch(this, function(_idxs, licenses) {
          this.askDeleteLicenses(licenses);
        }),
      });
      const columnsOverview = [
        {
          name: 'licenseCode',
          label: _('License code'),
          width: '66px',
        },
        {
          name: 'productId',
          label: _('Medium ID'),
          width: '66px',
          formatter: function(value) {
            if (value && value.startsWith('urn:bilo:medium:')) {
              value = value.slice(16, value.length);
            }
            return value;
          },
        },
        {
          name: 'productName',
          label: _('Medium'),
          width: '150px',
        },
        {
          name: 'publisher',
          label: _('Publisher'),
          width: '50px',
        },
        {
          name: 'licenseTypeLabel',
          label: _('License type'),
          width: '66px',
        },
        {
          name: 'for',
          label: _('For'),
          width: '66px',
        },
        {
          name: 'countAquired',
          label: _('Max. Users'),
          width: '66px',
        },
        {
          name: 'countAssigned',
          label: _('Assigned'),
          width: '66px',
        },
        {
          name: 'countExpired',
          label: _('Expired'),
          width: '66px',
        },
        {
          name: 'countAvailable',
          label: _('Available'),
          width: '66px',
        },
        {
          name: 'expiryDate',
          label: _('Expiry date'),
          width: '100px',
          formatter: function(value, object) {
            if (value) {
              value = dateLocale.format(new Date(value), {
                fullYear: true,
                selector: 'date',
              });
              return value;
            }
            if (object.usageStatus) {
              return _('unlimited');
            } else {
              return _('undefined');
            }
          },
        },
      ];

      this._grid = new Grid({
        actions: actions,
        columns: columnsOverview,
        moduleStore: store('licenseCode', 'licenses'),
        sortIndex: -11,
        addTitleOnCellHoverIfOverflow: true,
        class: 'licensesTable__licenses',
        gridOptions: {
          selectionMode: 'single',
        },
        selectorType: 'radio',
      });

      this.addChild(this._searchForm);
      this.addChild(this._grid);
    },
  });
});
