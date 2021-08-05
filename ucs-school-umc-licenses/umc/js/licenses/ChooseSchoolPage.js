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
	"dojox/html/entities",
	"umc/tools",
	"umc/widgets/ComboBox",
	"umc/widgets/Form",
	"umc/widgets/Page",
	"umc/widgets/Text",
	"umc/i18n!umc/modules/licenses"
], function(declare, lang, entities, tools, ComboBox, Form, Page, Text, _) {

	return declare("umc.modules.licenses.ChooseSchoolPage", [ Page ], {
		//// overwrites
		fullWidth: true,


		//// self
		onSchoolChosen: function(school) {
			// event stub
		},

		//// lifecycle
		buildRendering: function() {
			this.inherited(arguments);

			this.standbyDuring(
				tools.umcpCommand('licenses/schools').then(lang.hitch(this, function(response) {
					const schools = response.result;
					const hasMultipleSchools = schools.length > 1;

					if (schools.length === 1) {
						this.onSchoolChosen(schools[0], hasMultipleSchools);
					} else {
						const form = new Form({
							widgets: [{
								type: Text,
								size: 'One',
								name: 'headerText',
								content: '<h2>' + entities.encode(_('Please select a school')) + '</h2>'
							}, {
								type: ComboBox,
								name: 'school',
								label: _('School'),
								size: 'OneThirds',
								staticValues: schools,
								sortStaticValues: true,
							}],
							buttons: [{
								name: 'submit',
								label: _('Next')
							}],
							layout: [
								['headerText'],
								['school', 'submit'],
							],
						});
						form.on('submit', lang.hitch(this, function() {
							const schoolId = form.get('value').school;
							const school = schools.find(function(school) {
								return school.id === schoolId;
							});
							this.onSchoolChosen(school, hasMultipleSchools);
						}));

						this.addChild(form);
					}
				}))
			);
		},
	});
});
