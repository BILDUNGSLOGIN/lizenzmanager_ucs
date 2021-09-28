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
	"dojo/aspect",
	"dojo/on",
	"dojo/mouse",
	"dojo/query",
	"dojo/date/locale",
	"dojox/html/entities",
	"dijit/Tooltip",
	"umc/store",
	"umc/widgets/Page",
	"umc/widgets/Grid",
	"umc/widgets/SearchForm",
	"umc/widgets/Text",
	"umc/widgets/TextBox",
	"put-selector/put",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, dom, domClass, aspect, on, mouse, query, dateLocale, entities, Tooltip, store, Page, Grid,
		SearchForm, Text, TextBox, put, _) {

	return declare("umc.modules.licenses.ProductSearchPage", [ Page ], {
		//// overwrites
		fullWidth: true,


		//// self
		standbyDuring: null, // required parameter
		schoolId: null, // required parameter
		moduleFlavor: null, // required parameter
		showChangeSchoolButton: false,

		_grid: null,
		_searchForm: null,

		alloction: null,
		_setAllocationAttr: function(allocation) {
			domClass.remove(this._assignmentText.domNode, 'dijitDisplayNone');
			const count = allocation.usernames.length;
			const id = this.id + '-tooltipNode';
			const msg = `
				<p>
					${entities.encode(
						count === 1 ?
						_('Assign licenses to 1 selected user.')
						: _('Assign licenses to %s selected users.', count)
					)}
					<span id="${id}" class="licensesShowSelectedUsers">
						(${entities.encode(_("show selected users"))})
					</span>
				</p>
				<p>
					${entities.encode(_('Choose the medium for which you want to assign licenses.'))}
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

		onBack: function() {
			// event stub
		},

		onProductChosen: function() {
			// event stub
		},

		onChangeUsers: function() {
			// event stub
		},

		onChooseDifferentSchool: function() {
			// event stub
		},

		onShowProduct: function(productId) {
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
					label: _('Change user selection'),
					callback: lang.hitch(this, 'onChangeUsers'),
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
				type: TextBox,
				name: 'pattern',
				label: '&nbsp;',
				inlineLabel: _('Search licensed media'),
			}];
			this._searchForm = new SearchForm({
				'class': 'umcUDMSearchForm umcUDMSearchFormSimpleTextBox',
				region: 'nav',
				widgets: widgets,
				layout: [
					['pattern', 'submit'],
				],
				onSearch: lang.hitch(this, function(values) {
					values.school = this.schoolId;
					this._grid.filter(values);
				}),
			});

			const actions = [];
			if (this.moduleFlavor === 'licenses/allocation') {
				actions.push({
					name: 'edit',
					label: _('Assign licenses'),
					isStandardAction: true,
					isContextAction: true,
					isMultiAction: false,
					callback: lang.hitch(this, function(_idxs, products) {
						this.onProductChosen(products[0].productId, this.allocation.usernames);
					}),
				});
			} else {
				actions.push({
					name: 'edit',
					label: _('Show details'),
					isStandardAction: true,
					isContextAction: true,
					isMultiAction: false,
					callback: lang.hitch(this, function(_idxs, products) {
						this.onShowProduct(products[0].productId);
					}),
				});
			}
			const columns = [{
				name: 'productId',
				label: _('Medium ID'),
			}, {
				name: 'title',
				label: _('Medium'),
			}, {
				name: 'publisher',
				label: _('Publisher'),
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
				name: 'latestDeliveryDate',
				label: _('Import date'),
				formatter: function(value, object) {
					if (value) {
						value = dateLocale.format(new Date(value), {
							fullYear: true,
							selector: 'date',
						});
					}
					return value;
				},
			}];
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: store('productId', 'licenses/products'),
				sortIndex: -8,
				addTitleOnCellHoverIfOverflow: true,
				gridOptions: {
					selectionMode: 'single',
				},
				selectorType: 'radio',
			});
			// FIXME(?) usage of private inherited variables
			aspect.around(this._grid._grid, 'renderRow', lang.hitch(this, function(renderRow) {
				return lang.hitch(this, function(item, options) {
					const rowNode = renderRow.call(this._grid._grid, item, options);
					if (item.cover) {
					 	// .field-title should always exist. just to be safe
						const tooltipTarget = query('.field-title', rowNode)[0] || rowNode;
						on(rowNode, mouse.enter, function() {
							Tooltip.show(_('Loading cover...'), tooltipTarget);
							let showImage = true;
							const img = put(document.body, `img.dijitOffScreen.licensesCover[src="${item.cover}"]`);
							on(img, 'load', function() {
								if (showImage) {
									const innerHTML = `<img src="${item.cover}" style="width: ${img.clientWidth}px; height: ${img.clientHeight}px">`;
									Tooltip.show(innerHTML, tooltipTarget);
								}
							});
							on(img, 'error', function() {
								if (showImage) {
									Tooltip.show(_('Cover not found'), tooltipTarget);
								}
							});
							on.once(rowNode, mouse.leave, function() {
								showImage = false;
								Tooltip.hide(tooltipTarget);
							});
						});
					}
					return rowNode;
				})
			}));

			this.addChild(this._assignmentText);
			this.addChild(this._searchForm);
			this.addChild(this._grid);
		},
	});
});
