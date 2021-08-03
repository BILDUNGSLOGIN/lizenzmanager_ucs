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
	"dojo/on",
	"dojox/html/entities",
	"umc/store",
	"umc/tools",
	"umc/widgets/Module",
	"./licenses/ChooseSchoolPage",
	"./licenses/DetailPage",
	"./licenses/SearchPage",
	"./licenses/UserSelectionPage",
	"umc/i18n!umc/modules/licenses",
	"xstyle/css!./licenses.css"
], function(declare, lang, on, entities, store, tools, Module, ChooseSchoolPage, DetailPage, SearchPage, UserSelectionPage, _) {

	return declare("umc.modules.licenses", [ Module ], {
		//// overwrites
		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid',
			_detailPage: 'searchpage-grid',
		},


		//// self
		_chooseSchoolPage: null,
		_searchPage: null,
		_detailPage: null,
		_userSelectionPage: null,

		_schools: null,



		_buildRendering: function(schoolId, hasMultipleSchools) {
			this._searchPage = new SearchPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
				schoolId: schoolId,
				hasMultipleSchools: hasMultipleSchools,
			});
			this._detailPage = new DetailPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
			});

			this._userSelectionPage = new UserSelectionPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
				schoolId: schoolId,
			});

			on(this._searchPage, 'editLicense', lang.hitch(this, function(licenseId) {
				// TODO move to DetailPage
				const request = tools.umcpCommand('licenses/get', {
					licenseId: licenseId,
				}).then(lang.hitch(this, function(response) {
					const license = response.result;
					this.set('title', this.defaultTitle + ': ' + entities.encode(license.licenseCode));
					this._detailPage.set('license', license);
					this.selectChild(this._detailPage);
				}));
				this.standbyDuring(request);
			}));
			on(this._searchPage, 'chooseDifferentSchool', lang.hitch(this, function() {
				this.selectChild(this._chooseSchoolPage);
			}));

			on(this._detailPage, 'back', lang.hitch(this, function() {
				this.resetTitle();
				this.selectChild(this._searchPage);
			}));
			on(this._userSelectionPage, 'back', lang.hitch(this, function() {
				this.resetTitle();
				this.selectChild(this._searchPage);
			}));

			this.addChild(this._searchPage);
			this.addChild(this._detailPage);
			this.addChild(this._userSelectionPage);

			if (this.moduleFlavor === 'licenses/allocation') {
				this.selectChild(this._userSelectionPage);
			} else {
				this.selectChild(this._searchPage);
			}
		},


		//// lifecycle
		buildRendering: function() {
			this.inherited(arguments);
			this._chooseSchoolPage = new ChooseSchoolPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
			});
			on(this._chooseSchoolPage, 'schoolChosen', lang.hitch(this, function(schoolId, hasMultipleSchools) {
				this._buildRendering(schoolId, hasMultipleSchools);
			}));
			this.addChild(this._chooseSchoolPage);
		},
	});
});
