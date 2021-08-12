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
	"dojo/store/Memory",
	"dojo/store/Observable",
	"dijit/_WidgetBase",
	"dijit/_TemplatedMixin",
	"dojox/html/entities",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Page",
	"umc/widgets/Grid",
	"umc/widgets/CheckBox",
	"put-selector/put",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, Memory, Observable, _WidgetBase, _TemplatedMixin, entities, tools, dialog, Page, Grid, CheckBox, put, _) {

	const _Table = declare("umc.modules.licenses.Table", [_WidgetBase, _TemplatedMixin], {
		//// overwrites
		templateString: `
			<div class="licensesTable">
				<div
					class="licensesTable__coverWrapper"
				>
					<img
						data-dojo-attach-point="_coverNode"
						class="licensesTable__cover"
					>
				</div>
				<div
					data-dojo-attach-point="_tableNode"
					class="licensesTable__data"
				></div>
			</div>
		`,


		//// self
		standbyDuring: null, // required

		license: null,
		_setLicenseAttr: function(license) {
			this._coverNode.src = license.cover;
			this._tableNode.innerHTML = '';

			function e(id) {
				let val = license[id];
				if (typeof val === 'string') {
					val = entities.encode(val);
				}
				return val;
			}

			const ignore = lang.hitch(this, function ignore() {
				this._ignore = new CheckBox({
					value: license.ignore
				});
				return this._ignore.domNode;
			});

			const data = [
				[_('Publisher'),       e('publisher'),      _('Usage'),          e('usage')],
				[_('Product ID'),      e('productId'),      _('Delivery'),       e('importDate')],
				[_('Title'),           e('productName'),    _('Validity start'), e('validityStart')],
				[_('Author'),          e('author'),         _('Validity end'),   e('validityEnd')],
				[_('Platform'),        e('platform'),       _('Validity span'),  e('validitySpan')],
				[_('License code'),    e('licenseCode'),    _('Ignore'),         ignore()],
				[_('License type'),    e('licenseType'),    _('Aquired'),        e('countAquired')],
				[_('Reference'),       e('reference'),      _('Assigned'),       e('countAllocated')],
				[_('Special license'), e('specialLicense'), _('Expired'),        e('countExpired')],
				['',                   '',                  _('Available'),      e('countAllocatable')],
			];

			for (const row of data) {
				put(this._tableNode,
					'div.licensesTable__dataLabel', row[0],
					'+ div', row[1],
					'+ div.licensesTable__dataLabel', row[2],
					'+ div', row[3]
				);
			}
			this._set('license', license);
		},

		ignoreChanged: function() {
			return this.getIgnore() !== this.license.ignore;
		},

		getIgnore: function() {
			return this._ignore.get('value');
		},
	});

	return declare("umc.modules.licenses.LicenseDetailPage", [ Page ], {
		//// overwrites
		fullWidth: true,


		//// self
		_table: null,
		_grid: null,

		license: null,
		_setLicenseAttr: function(license) {
			this._table.set('license', license);
			this._grid.moduleStore.setData(license.users);
			this._grid.filter();
			this._set('license', license);
		},

		load: function(licenseId) {
			return this.standbyDuring(
				tools.umcpCommand('licenses/get', {
					licenseId: licenseId,
				}).then(lang.hitch(this, function(response) {
					const license = response.result;
					this.set('license', license);
					return license.licenseCode;
				}))
			);
		},

		save: function() {
			if (!this._table.ignoreChanged()) {
				this.onBack();
			} else {
				this.standbyDuring(tools.umcpCommand('licenses/set_ignore', {
					license_id: this.license.licenseId,
					ignore: this._table.getIgnore(),
				}).then(lang.hitch(this, function(response) {
					console.log(response);
					this.onBack();
				})));
			}
		},

		removeLicense: function(userDNs) {
			tools.umcpCommand('licenses/remove_from_users', {
				user_dns: userDNs,
			}).then(lang.hitch(this, function(response) {
				console.log(response);
				// TODO update Grid
			}));
		},

		back: function() {
			if (this._table.ignoreChanged()) {
				dialog.confirm(_('There are unsaved changes. Are you sure to cancel?'), [{
					label: _('Continue editing'),
				}, {
					label: _('Discard changes'),
					'default': true,
					callback: lang.hitch(this, 'onBack')
				}]);
			} else {
				this.onBack();
			}
		},

		onBack: function() {
			// event stub
		},


		//// lifecycle
		postMixInProperties: function() {
			this.headerButtons = [{
				name: 'save',
				label: _('Save'),
				callback: lang.hitch(this, 'save'),
			}, {
				name: 'close',
				label: _('Back'),
				callback: lang.hitch(this, 'back'),
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._table = new _Table({});

			const actions = [{
				name: 'delete',
				label: _('Remove license'),
				isStandardAction: true,
				isContextAction: true,
				isMultiAction: true,
				canExecute: function(user) {
					return user.status === 'allocated';
				},
				callback: lang.hitch(this, function(idxs, users) {
					this.removeLicense(users.map(function(user) {
						return user.dn;
					}));
				}),
			}];
			const columns = [{
				name: 'username',
				label: _('User'),
			}, {
				name: 'status',
				label: _('Status'),
			}, {
				name: 'allocationDate',
				label: _('Date of assignment'),
			}];
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: new Observable(new Memory({
					data: [],
					idProperty: 'dn'
				})),
			});

			this.addChild(this._table);
			this.addChild(this._grid);
		},
	});
});
