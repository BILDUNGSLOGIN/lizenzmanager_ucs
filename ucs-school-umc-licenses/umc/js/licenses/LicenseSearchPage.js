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
	"dojo/dom",
	"dojo/dom-class",
	"dojo/on",
	"dojox/html/entities",
	"dijit/Tooltip",
	"umc/dialog",
	"umc/store",
	"umc/tools",
	"umc/widgets/Page",
	"umc/widgets/Grid",
	"umc/widgets/CheckBox",
	"umc/widgets/DateBox",
	"umc/widgets/ComboBox",
	"umc/widgets/SearchForm",
	"umc/widgets/Text",
	"umc/widgets/TextBox",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, dom, domClass, on, entities, Tooltip, dialog, store, tools, Page, Grid, CheckBox, DateBox,
		ComboBox, SearchForm, Text, TextBox, _) {

	return declare("umc.modules.licenses.LicenseSearchPage", [ Page ], {
		//// overwrites
		fullWidth: true,


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
				const widget = this._searchForm.getWidget(widgetName);
				if (widget) {
					widget.set('visible', this._isAdvancedSearch);
				}
			}));
			this._searchForm.getWidget('pattern').set('visible', !this._isAdvancedSearch);

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

		allocation: null,
		_setAllocationAttr: function(allocation) {
			domClass.remove(this._assignmentText.domNode, 'dijitDisplayNone');
			const count = allocation.usernames.length;
			const id = this.id + '-tooltip';
			const msg = `
				<p>
					${entities.encode(
						count === 1 ?
						_('Assign licenses to 1 selected user.')
						: _('Assign licenses to %s selected users.', count)
					)}
					<span id="${id}" class="licensesShowSelectedUsers">(show selected users)</span>
				</p>
				<p>
					${entities.encode(_('Choose the licenses you want to assign.'))}
				</p>
			`.trim();
			this._assignmentText.set('content', msg);
			const node = dom.byId(id);
			on(node, 'click', lang.hitch(this, function(evt) {
				let label = '';
				for (const username of this.allocation.usernames) {
					label += `<div>${entities.encode(username)}</div>`;
				}
				Tooltip.show(label, node);
				evt.stopImmediatePropagation();
				on.once(window, "click", lang.hitch(this, function(event) {
					Tooltip.hide(node);
				}));
			}));
			this._set('allocation', allocation);
		},

		query: function() {
			this.standbyDuring(
				this._searchForm.ready().then(lang.hitch(this, function() {
					this._searchForm.submit();
				}))
			);
		},

		onShowLicense: function(licenseCode) {
			// event stub
		},

		onChooseDifferentSchool: function() {
			// event stub
		},

		onChangeUsers: function() {
			// event stub
		},

		onChangeProduct: function() {
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
					name: 'changeUsers',
					label: _('Change user selection'),
					callback: lang.hitch(this, 'onChangeUsers'),
				});
				headerButtons.push({
					name: 'close',
					label: _('Change medium'),
					callback: lang.hitch(this, 'onChangeProduct'),
				});
			}
			this.headerButtons = headerButtons;
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._assignmentText = new Text({
				region: 'nav',
				'class': 'dijitDisplayNone',
			});

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
				type: ComboBox,
				name: 'licenseType',
				label: _('License type'),
				staticValues: [{id: '', label: ''}],
				dynamicValues: 'licenses/license_types',
				size: 'TwoThirds',
				visible: false,
			}, {
				type: TextBox,
				name: 'userPattern',
				label: _('User identification'),
				description: _("Search for licenses that have this user assigned. (Searches for 'first name', 'last name' and 'username')"),
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
			if (this.moduleFlavor !== 'licenses/allocation') {
				widgets.push({
					type: TextBox,
					name: 'product',
					label: _('Medium name'),
					size: 'TwoThirds',
					visible: false,
				}, {
					type: TextBox,
					name: 'productId',
					label: _('Medium ID'),
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
					staticValues: [{id: '', label: ''}],
					dynamicValues: 'licenses/publishers',
					size: 'TwoThirds',
					visible: false,
				});
			}
			let layout = null;
			if (this.moduleFlavor === 'licenses/allocation') {
				layout = [
					['timeFrom', 'timeTo', 'userPattern'],
					['licenseType', 'licenseCode', 'pattern', 'submit', 'toggleSearch'],
				];
			} else {
				layout = [
					['timeFrom', 'timeTo', 'onlyAvailableLicenses'],
					['publisher', 'licenseType', 'userPattern'],
					['productId', 'product', 'licenseCode', 'pattern', 'submit', 'toggleSearch'],
				];
			}
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
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					values.isAdvancedSearch = this._isAdvancedSearch;
					values.school = this.schoolId;
					if (this.moduleFlavor === 'licenses/allocation') {
						values.onlyAvailableLicenses = true;
						values.allocationProductId = this.allocation.productId;
					}
					this._grid.filter(values);
				}),
			});
			domClass.add(
				this._searchForm.getWidget('licenseCode').$refLabel$.domNode,
				'umcSearchFormElementBeforeSubmitButton'
			);

			const actions = [];
			if (this.moduleFlavor === 'licenses/allocation') {
				actions.push({
					name: 'assign',
					label: _('Assign licenses'),
					isStandardAction: true,
					isContextAction: true,
					isMultiAction: true,
					callback: lang.hitch(this, function(_idxs, licenses) {
						tools.umcpCommand('licenses/assign_to_users', {
							licenseCodes: licenses.map(license => license.licenseCode),
							usernames: this.allocation.usernames,
						}).then(lang.hitch(this, function(response) {
							const result = response.result;
							let msg = '';
							if (result.notEnoughLicenses) {
								msg += '<p>' +
									entities.encode(_('The number of selected licenses is not sufficient to assign a license to all selected users. Therefore, no licenses have been assigned. Please reduce the number of selected users or select more licenses and repeat the process.')) +
									'</p>';
								dialog.alert(msg, _('Assigning licenses failed'));
								return;
							}
							if (result.countSuccessfulAssignments) {
								if (result.countSuccessfulAssignments === this.allocation.usernames.length) {
									msg += '<p>' +
										entities.encode(
											_(
												'Licenses were successfully assigned to all %s selected users.',
												result.countSuccessfulAssignments
											)
										) +
										'</p>';
								} else {
									msg += '<p>' +
										entities.encode(
											_(
												'Licenses were successfully assigned to %s of the %s selected users.',
												result.countSuccessfulAssignments, this.allocation.usernames.length
											)
										) +
										'</p>';
								}
							}
							if (result.failedAssignments.length) {
								msg += '<p>';
								msg += result.countSuccessfulAssignments > 0 ?
									entities.encode(_('Some selected users could not be assigned licenses:'))
									: entities.encode(_('Failed to assign licenses to the selected users:'));
								msg += '<ul>';
								for (const error of result.failedAssignments) {
									msg += '<li>' + entities.encode(error) + '</li>';
								}
								msg += '</ul>';
								msg += '</p>';
							}
							if (result.validityInFuture.length) {
								msg += '<p>';
								msg += entities.encode(
									_('Warning: The validity for the following assigned licenses lies in the future:')
								);
								msg += '<ul>';
								for (const licenseCode of result.validityInFuture) {
									msg += '<li>' + entities.encode(licenseCode) + '</li>';
								}
								msg += '</ul>';
								msg += '</p>';
							}
							const title = _('Assigning licenses');
							dialog.alert(msg, title);
						}));
					}),
				});
			} else {
				actions.push({
					name: 'edit',
					label: _('Edit'),
					iconClass: 'umcIconEdit',
					isStandardAction: true,
					isContextAction: true,
					isMultiAction: false,
					callback: lang.hitch(this, function(_idxs, licenses) {
						this.onShowLicense(licenses[0].licenseCode);
					}),
				});
			}
			const columns = [{
				name: 'licenseCode',
				label: _('License code'),
			}, {
				name: 'productId',
				label: _('Medium ID'),
			}, {
				name: 'productName',
				label: _('Medium'),
			}, {
				name: 'publisher',
				label: _('Publisher'),
			}, {
				name: 'licenseTypeLabel',
				label: _('License type'),
			}, {
				name: 'countAquired',
				label: _('Acquired'),
				width: 'adjust',
			}, {
				name: 'countAssigned',
				label: _('Assigned'),
				width: 'adjust',
			}, {
				name: 'countExpired',
				label: _('Expired'),
				width: 'adjust',
			}, {
				name: 'countAvailable',
				label: _('Available'),
				width: 'adjust',
			}, {
				name: 'importDate',
				label: _('Delivery'),
			}];
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: store('licenseCode', 'licenses'),
				sortIndex: -10,
				addTitleOnCellHoverIfOverflow: true,
			});

			this.addChild(this._assignmentText);
			this.addChild(this._searchForm);
			this.addChild(this._grid);
		},
	});
});
