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
      'dojo/dom-class',
      'umc/widgets/SuggestionBox',
      'umc/widgets/TextBox',
      'umc/widgets/DateBox',
      'umc/widgets/ComboBox',
      'umc/widgets/CheckBox',
      'umc/widgets/SearchForm',
      'umc/i18n!umc/modules/licenses'],
    function(declare, lang, domClass, SuggestionBox, TextBox, DateBox, ComboBox,
        CheckBox, SearchForm, _) {
      return declare('umc.modules.licenses.LicenseSearchformMixin', [], {
        onChooseDifferentClass: function() {
          const workgroupWidget = this._searchForm.getWidget('workgroup');
          workgroupWidget.setValue('');
        },

        onChooseDifferentWorkgroup: function() {
          const classWidget = this._searchForm.getWidget('class');
          classWidget.setValue('');
        },

        refreshGrid(value) {},

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
            'validStatus',
            'usageStatus',
            'expiryDateFrom',
            'expiryDateTo',
            'workgroup',
            'class'].forEach(lang.hitch(this, function(widgetName) {
            const widget = this._searchForm.getWidget(widgetName);
            if (widget) {
              widget.set('visible', this._isAdvancedSearch);
            }
          }));

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

        createLicenseSearchWidget: function() {
          this._isAdvancedSearch = false;

          this._licenseTypes = [
            {id: '', label: ''},
            {id: 'SINGLE', label: _('Single license')},
            {id: 'VOLUME', label: _('Volume license')},
            {
              id: 'WORKGROUP', label: _('Workgroup license'),
            },
            {
              id: 'SCHOOL', label: _('School license'),
            }];

          const widgets = [
            {
              type: DateBox,
              name: 'timeFrom',
              visible: false,
              label: _('Start import period'),
              size: 'TwoThirds',
            }, {
              type: DateBox,
              name: 'timeTo',
              label: _('End import period'),
              size: 'TwoThirds',
              visible: false,
            }, {
              type: ComboBox,
              name: 'licenseType',
              label: _('License type'),
              staticValues: this._licenseTypes,
              size: 'TwoThirds',
              visible: false,
            }, {
              type: TextBox,
              name: 'userPattern',
              label: _('User ID'),
              description: _(
                  'Search for licenses that have this user assigned. (Searches for \'first name\', \'last name\' and \'username\')'),
              size: 'TwoThirds',
              visible: false,
            }, {
              type: TextBox,
              name: 'licenseCode',
              label: _('License code'),
              size: 'TwoThirds',
              visible: false,
            }, {
              type: TextBox,
              name: 'pattern',
              label: '&nbsp;',
              inlineLabel: _('Search licenses'),
            }];
          widgets.push({
                type: TextBox,
                name: 'product',
                label: _('Media Title'),
                size: 'TwoThirds',
                visible: false,
              }, {
                type: TextBox,
                name: 'productId',
                label: _('Medium ID'),
                size: 'TwoThirds',
                visible: false,
                formatter: function(value) {
                  if (value && value.startsWith('urn:bilo:medium:')) {
                    value = value.slice(16, value.length);
                  }
                  return value;
                },
              }, {
                type: CheckBox,
                name: 'onlyAvailableLicenses',
                label: _('Only assignable licenses'),
                value: false,
                size: 'TwoThirds',
                visible: false,
              }, {
                type: ComboBox,
                name: 'publisher',
                label: _('Publisher'),
                staticValues: [{id: '', label: ''}],
                dynamicValues: 'licenses/publishers',
                dynamicOptions: {
                  school: this.getSchoolId(),
                },
                size: 'TwoThirds',
                visible: false,
              }, {
                type: ComboBox,
                name: 'workgroup',
                label: _('Assigned to Workgroup'),
                staticValues: [{id: '', label: ''}],
                dynamicValues: 'licenses/workgroups',
                dynamicOptions: {
                  school: this.getSchoolId(),
                },
                size: 'TwoThirds',
                visible: false,
                onChange: lang.hitch(this, function(values) {
                  this.onChooseDifferentWorkgroup(values);
                }),
              }, {
                type: SuggestionBox,
                name: 'class',
                label: _('Assigned to Class'),
                staticValues: [{id: '', label: ''}],
                dynamicValues: 'licenses/classes',
                dynamicOptions: {
                  school: this.getSchoolId(),
                },
                size: 'TwoThirds',
                visible: false,
                onChange: lang.hitch(this, function(values) {
                  this.onChooseDifferentClass(values);
                }),
              }, {
                type: ComboBox,
                name: 'validStatus',
                label: _('Validity status'),
                staticValues: [
                  {
                    id: '', label: '',
                  }, {
                    id: '0', label: _('invalid'),
                  }, {
                    id: '1', label: _('valid'),
                  }],
                size: 'TwoThirds',
                visible: false,
              }, {
                type: ComboBox,
                name: 'usageStatus',
                label: _('Usage status'),
                staticValues: [
                  {
                    id: '', label: '',
                  }, {
                    id: '0', label: _('not activated'),
                  }, {
                    id: '1', label: _('activated'),
                  }],
                size: 'TwoThirds',
                visible: false,
              },
              {
                type: DateBox,
                name: 'expiryDateFrom',
                visible: false,
                label: _('Expiry date start'),
                size: 'TwoThirds',
              },
              {
                type: DateBox,
                name: 'expiryDateTo',
                visible: false,
                label: _('Expiry date end'),
                size: 'TwoThirds',
              },
          );

          let layout = [
            ['timeFrom', 'timeTo', 'onlyAvailableLicenses'],
            ['publisher', 'licenseType', 'userPattern'],
            ['workgroup', 'class'],
            ['validStatus', 'usageStatus'],
            ['expiryDateFrom', 'expiryDateTo'],
            [
              'productId',
              'product',
              'licenseCode',
              'pattern',
              'submit',
              'toggleSearchLabel',
              'toggleSearch']];
          const buttons = [
            {
              name: 'toggleSearch', labelConf: {
                class: 'umcFilters',
              }, label: _('Filters'), iconClass: 'umcDoubleRightIcon',

              callback: lang.hitch(this, function() {
                this._toggleSearch();
              }),
            }];

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
              'umcSearchFormElementBeforeSubmitButton');

        },
      });
    });
