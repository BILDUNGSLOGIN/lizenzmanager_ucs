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
	"umc/store",
	"umc/widgets/ComboBox",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/SearchBox",
	"umc/widgets/SearchForm",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, store, ComboBox, Grid, Page, SearchBox, SearchForm, _) {

	return declare("umc.modules.licenses.UserSelectionPage", [ Page ], {
		//// overwrites
		fullWidth: true,


		//// self
		// standbyDuring: null, // required

		onBack: function() {
			// event stub
		},


		//// lifecycle
		// postMixInProperties: function() {
			// this.headerButtons = [{
				// name: 'close',
				// label: _('Back'),
				// callback: lang.hitch(this, 'onBack'),
			// }];
		// },

		buildRendering: function() {
			this.inherited(arguments);

			const widgets = [{
				type: ComboBox,
				name: 'class',
				staticValues: [{id: '__all__', label: _('All classes')}],
				dynamicValues: 'licenses/classes',
				dynamicOptions: {
					school: this.schoolId,
				},
				label: _('Class'),
				size: 'TwoThirds',
			}, {
				type: ComboBox,
				name: 'workgroup',
				staticValues: [{id: '__all__', label: _('All workgroups')}],
				dynamicValues: 'licenses/workgroups',
				dynamicOptions: {
					school: this.schoolId,
				},
				label: _('Workgroup'),
				size: 'TwoThirds',
			}, {
				type: SearchBox,
				name: 'pattern',
				label: '&nbsp',
				inlineLabel: _('Search user'),
				size: 'TwoThirds',
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				}),
			}];
			this._searchForm = new SearchForm({
				region: 'nav',
				widgets: widgets,
				layout: [
					['class', 'workgroup', 'pattern'],
				],
				hideSubmitButton: true,
				onSearch: lang.hitch(this, function(values) {
					this._grid.filter(values);
				}),
			});

			const actions = [{
				name: 'allocate',
				label: _('Allocate licenses'),
				isStandardAction: true,
				isContextAction: true,
				isMultiAction: true,
				callback: lang.hitch(this, function(_idxs, licenses) {
					console.log('allocating');
					// this.onEditLicense(licenses[0].licenseId);
				}),
			}];
			const columns = [{
				name: 'username',
				label: _('Username'),
			}, {
				name: 'lastname',
				label: _('Last name'),
			}, {
				name: 'firstname',
				label: _('First name'),
			}, {
				name: 'class',
				label: _('Class'),
			}, {
				name: 'workgroup',
				label: _('Workgroup'),
			}];
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: store('userId', 'licenses/users'),
			});

			this.addChild(this._searchForm);
			this.addChild(this._grid);

			this.standbyDuring(
				this._searchForm.ready().then(lang.hitch(this, function() {
					this._searchForm.submit();
				}))
			);
		},
	});
});
