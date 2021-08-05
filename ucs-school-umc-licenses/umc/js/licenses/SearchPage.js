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
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/dom-class",
	"dojo/on",
	"dojo/mouse",
	"dijit/Tooltip",
	"umc/store",
	"umc/widgets/Page",
	"umc/widgets/Grid",
	"umc/widgets/CheckBox",
	"umc/widgets/DateBox",
	"umc/widgets/ComboBox",
	"umc/widgets/SearchForm",
	"umc/widgets/TextBox",
	"put-selector/put",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, domClass, on, mouse, Tooltip, store, Page, Grid, CheckBox, DateBox, ComboBox, SearchForm, TextBox, put, _) {

	return declare("umc.modules.licenses.SearchPage", [ Page ], {
		//// overwrites
		fullWidth: true,

		_onShow: function() {
			this.standbyDuring(
				this._searchForm.ready().then(lang.hitch(this, function() {
					this._searchForm.submit();
				}))
			);
		},


		//// self
		standbyDuring: null, // required parameter
		schoolId: null, // required parameter
		moduleFlavor: null, // required parameter
		showChangeSchoolButton: false,

		_grid: null,
		_searchForm: null,

		_isAdvancedSearch: false,

		_toggleSearch: function() {
			this._isAdvancedSearch = !this._isAdvancedSearch;

			// reset widgets
			if (this._isAdvancedSearch) {
				this._searchForm.getWidget('pattern').reset();
			} else {
				this._searchForm.widgets.forEach(lang.hitch(this, function(widget) {
					if (widget.name !== 'pattern') {
						this._searchForm.getWidget(widget.name).reset();
					}
				}));
			}

			// toggle visibility
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
			].forEach(lang.hitch(this, function(widgetName) {
				this._searchForm.getWidget(widgetName).set('visible', this._isAdvancedSearch);
			}));
			this._searchForm.getWidget('pattern').set('visible', !this._isAdvancedSearch);
			if (this.moduleFlavor === 'licenses/allocation') {
				this._searchForm.getWidget('onlyAvailableLicenses').set('visible', false);
			}

			// update toggle button
			const button = this._searchForm.getButton('toggleSearch');
			if (this._isAdvancedSearch) {
				button.set('label', _('Simple search'));
				button.set('iconClass', 'umcDoubleLeftIcon');
			} else {
				button.set('label', _('Advanced search'));
				button.set('iconClass', 'umcDoubleRightIcon');
			}
		},

		onEditLicense: function(licenseId) {
			// event stub
		},

		onChooseDifferentSchool: function() {
			// event stub
		},

		onBack: function() {
			// event stub
		},


		//// lifecycle
		postMixInProperties: function() {
			this.inherited(arguments);
			const headerButtons = [];
			if (this.showChangeSchoolButton) {
				headerButtons.push({
					name: 'changeSchool',
					label: _('Change school'),
					callback: lang.hitch(this, 'onChooseDifferentSchool'),
				});
			}
			if (this.moduleFlavor === 'licenses/allocation') {
				headerButtons.push({
					name: 'close',
					label: _('Back'),
					callback: lang.hitch(this, 'onBack'),
				});
			}
			this.headerButtons = headerButtons;
		},

		buildRendering: function() {
			this.inherited(arguments);

			const widgets = [{
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
				staticValues: [{id: '__all__', label: _('All publishers')}],
				dynamicValues: 'licenses/publishers',
				size: 'TwoThirds',
				visible: false,
			}, {
				type: ComboBox,
				name: 'licenseType',
				label: _('License type'),
				staticValues: [{id: '__all__', label: _('All license types')}],
				dynamicValues: 'licenses/license_types',
				size: 'TwoThirds',
				visible: false,
			}, {
				type: TextBox,
				name: 'userPattern',
				label: _('User identification'),
				// description: 'TODO description',
				size: 'TwoThirds',
				visible: false,
			}, {
				type: TextBox,
				name: 'productId',
				label: _('Product ID'),
				size: 'TwoThirds',
				visible: false,
			}, {
				type: TextBox,
				name: 'product',
				label: _('Product name'),
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
			const buttons = [{
				name: 'toggleSearch',
				showLabel: false,
				labelConf: {
					'class': 'umcSearchFormSubmitButton'
				},
				iconClass: 'umcDoubleRightIcon',
				label: _('Advanced search'),
				callback: lang.hitch(this, function() {
					this._toggleSearch();
				}),
			}];
			this._searchForm = new SearchForm({
				'class': 'umcUDMSearchForm umcUDMSearchFormSimpleTextBox',
				region: 'nav',
				widgets: widgets,
				buttons: buttons,
				layout: [
					['timeFrom', 'timeTo', 'onlyAvailableLicenses'],
					['publisher', 'licenseType', 'userPattern'],
					['productId', 'product', 'licenseCode', 'pattern', 'submit', 'toggleSearch'],
				],
				onSearch: lang.hitch(this, function(values) {
					values.school = this.schoolId;
					if (this.moduleFlavor === 'licenses/allocation') {
						values.onlyAvailableLicenses = true;
					}
					this._grid.filter(values);
				}),
			});
			domClass.add(this._searchForm.getWidget('licenseCode').$refLabel$.domNode, 'umcSearchFormElementBeforeSubmitButton');

			const actions = [{
				name: 'edit',
				label: _('Edit'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isContextAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, function(_idxs, licenses) {
					this.onEditLicense(licenses[0].licenseId);
				}),
			}];
			const columns = [{
				name: 'licenseCode',
				label: _('License code'),
			}, {
				name: 'productId',
				label: _('Product ID'),
			}, {
				name: 'productName',
				label: _('Product'),
			}, {
				name: 'publisher',
				label: _('Publisher'),
			}, {
				name: 'licenseType',
				label: _('License type'),
			}, {
				name: 'countAquired',
				label: _('Aquired'),
				width: '60px',
			}, {
				name: 'countAssigned',
				label: _('Assigned'),
				width: '60px',
			}, {
				name: 'countExpired',
				label: _('Expired'),
				width: '60px',
			}, {
				name: 'countAvailable',
				label: _('Available'),
				width: '60px',
			}, {
				name: 'importDate',
				label: _('Delivery'),
			}];
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: store('licenseId', 'licenses'),
				sortIndex: -10,
			});

			// add title attribute to table cell if text overflows (and shows ellipsis)
			on(this._grid.domNode, on.selector('.dgrid-cell', mouse.enter), lang.hitch(this, function(evt) {
				let node = evt.target;
				while (node && !domClass.contains(node, 'dgrid-cell')) {
					node = node.parentElement;
				}
				if (node && node.clientWidth < node.scrollWidth) {
					node.title = node.innerText;
					on.once(node, mouse.leave, function() {
						node.title = '';
					});
				}
			}));

			this.addChild(this._searchForm);
			this.addChild(this._grid);
		},
	});
});
