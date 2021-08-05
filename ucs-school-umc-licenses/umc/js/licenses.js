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
	"umc/widgets/Text",
	"./licenses/ChooseSchoolPage",
	"./licenses/DetailPage",
	"./licenses/SearchPage",
	"./licenses/UserSelectionPage",
	"umc/i18n!umc/modules/licenses",
	"xstyle/css!./licenses.css"
], function(declare, lang, on, entities, store, tools, Module, Text, ChooseSchoolPage, DetailPage, SearchPage, UserSelectionPage, _) {

	return declare("umc.modules.licenses", [ Module ], {
		//// overwrites
		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid',
			_detailPage: 'searchpage-grid',
			_userSelectionPage: 'searchpage-grid',
		},


		//// self
		_chooseSchoolPage: null,
		_searchPage: null,
		_detailPage: null,
		_userSelectionPage: null,

		_buildLicenses: function(schoolId, hasMultipleSchools) {
			if (this._searchPage) {
				this._searchPage.destroyRecursive();
			}
			if (this._detailPage) {
				this._detailPage.destroyRecursive();
			}

			this._searchPage = new SearchPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
				schoolId: schoolId,
				showChangeSchoolButton: hasMultipleSchools,
				moduleFlavor: this.moduleFlavor,
			});
			on(this._searchPage, 'chooseDifferentSchool', lang.hitch(this, function() {
				this._chooseDifferentSchool();
			}));
			on(this._searchPage, 'editLicense', lang.hitch(this, function(licenseId) {
				this._detailPage.load(licenseId).then(lang.hitch(this, function(licenseCode) {
					this.set('title', this.defaultTitle + ': ' + entities.encode(licenseCode));
					this.selectChild(this._detailPage);
				}));
			}));

			this._detailPage = new DetailPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
			});
			on(this._detailPage, 'back', lang.hitch(this, function() {
				this.resetTitle();
				this.selectChild(this._searchPage);
			}));

			this.addChild(this._searchPage);
			this.addChild(this._detailPage);

			this.selectChild(this._searchPage);
		},

		_schoolLabelWidget: null,
		schoolLabel: '&nbsp;',
		_setSchoolLabelAttr: function(schoolLabel) {
			if (!this._schoolLabelWidget) {
				this._schoolLabelWidget = new Text({
					content: '',
				});
				// FIXME usage of private variables
				this._top._left.addChild(this._schoolLabelWidget);
			}
			this._schoolLabelWidget.set('content', schoolLabel);
			this._set('schoolLabel', schoolLabel);
		},

		_chooseDifferentSchool: function() {
			this.set('schoolLabel', '&nbsp;');
			this.selectChild(this._chooseSchoolPage);
		},

		_buildAllocation: function(schoolId, hasMultipleSchools) {
			if (this._userSelectionPage) {
				this._userSelectionPage.destroyRecursive();
			}
			if (this._searchPage) {
				this._searchPage.destroyRecursive();
			}

			this._userSelectionPage = new UserSelectionPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
				schoolId: schoolId,
				showChangeSchoolButton: hasMultipleSchools,
			});
			on(this._userSelectionPage, 'chooseDifferentSchool', lang.hitch(this, function() {
				this._chooseDifferentSchool();
			}));

			this._searchPage = new SearchPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
				schoolId: schoolId,
				moduleFlavor: this.moduleFlavor,
			});


			this.addChild(this._userSelectionPage);
			this.addChild(this._searchPage);

			this.selectChild(this._userSelectionPage);
		},


		//// lifecycle
		buildRendering: function() {
			this.inherited(arguments);

			this._chooseSchoolPage = new ChooseSchoolPage({
				standbyDuring: lang.hitch(this, 'standbyDuring'),
			});
			on(this._chooseSchoolPage, 'schoolChosen', lang.hitch(this, function(school, hasMultipleSchools) {
				this.set('schoolLabel', _('for %(school)s', {school: entities.encode(school.label)}));
				switch (this.moduleFlavor) {
					case 'licenses/licenses':
						this._buildLicenses(school.id, hasMultipleSchools);
						break;
					case 'licenses/allocation':
						this._buildAllocation(school.id, hasMultipleSchools);
						break;
				}
			}));

			this.addChild(this._chooseSchoolPage);
		},
	});
});
