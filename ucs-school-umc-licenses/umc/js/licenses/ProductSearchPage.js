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
	"dojo/aspect",
	"dojo/on",
	"dojo/mouse",
	"dojo/query",
	"dijit/Tooltip",
	"umc/store",
	"umc/widgets/Page",
	"umc/widgets/Grid",
	"umc/widgets/SearchForm",
	"umc/widgets/TextBox",
	"put-selector/put",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, aspect, on, mouse, query, Tooltip, store, Page, Grid, SearchForm, TextBox, put, _) {

	return declare("umc.modules.licenses.ProductSearchPage", [ Page ], {
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

		onChooseDifferentSchool: function() {
			// event stub
		},

		onShowProduct: function(productId) {
			// event stub
		},


		//// lifecycle
		postMixInProperties: function() {
			this.inherited(arguments);
			if (this.showChangeSchoolButton) {
				this.headerButtons = [{
					name: 'changeSchool',
					label: _('Change school'),
					callback: lang.hitch(this, 'onChooseDifferentSchool'),
				}];
			}
		},

		buildRendering: function() {
			this.inherited(arguments);

			const widgets = [{
				type: TextBox,
				name: 'pattern',
				label: '&nbsp;',
				inlineLabel: _('Search licensed products'),
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

			const actions = [{
				name: 'edit',
				label: _('Edit'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isContextAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, function(_idxs, products) {
					this.onShowProduct(products[0].productId);
				}),
			}];
			const columns = [{
				name: 'productId',
				label: _('Product ID'),
			}, {
				name: 'productName',
				label: _('Product'),
			}, {
				name: 'publisher',
				label: _('Publisher'),
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
				name: 'lastImportDate',
				label: _('Last delivery'),
			}];
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: store('productId', 'licenses/products'),
				sortIndex: -8,
				addTitleOnCellHoverIfOverflow: true,
			});
			// FIXME(?) usage of private inherited variables
			aspect.around(this._grid._grid, 'renderRow', lang.hitch(this, function(renderRow) {
				return lang.hitch(this, function(item, options) {
					const rowNode = renderRow.call(this._grid._grid, item, options);
					if (item.cover) {
					 	// .field-productName should always exist. just to be safe
						const tooltipTarget = query('.field-productName', rowNode)[0] || rowNode;
						on(rowNode, mouse.enter, function() {
							Tooltip.show('loading cover...', tooltipTarget);
							let showImage = true;
							const img = put(document.body, `img.dijitOffScreen.licensesCover[src="${item.cover}]`);
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

			this.addChild(this._searchForm);
			this.addChild(this._grid);
		},
	});
});

