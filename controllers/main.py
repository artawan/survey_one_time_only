# -*- coding: utf-8 -*-

import logging

from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey

_logger = logging.getLogger(__name__)

class CustomSurvey(Survey):
    def _check_bad_cases(self, survey, token=None):
        res = super(CustomSurvey, self)._check_bad_cases(survey)

        # Check if user already fill current survey
        partner_id = request.env.user.partner_id.id
        user_input = request.env['survey.user_input']
        survey_data = user_input.sudo().search([('survey_id', '=', survey.id), ('partner_id', '=', partner_id), ('state', '=', 'done')], limit=1)

        if survey_data:
            return request.render('survey_one_time_only.already')

        return res

    @http.route()
    def start_survey(self, survey, token=None, **post):
        UserInput = request.env['survey.user_input']
        partner_id = request.env.user.partner_id.id

        # Test mode
        if token and token == "phantom":
            _logger.info("[survey] Phantom mode")
            user_input = UserInput.create({'survey_id': survey.id, 'test_entry': True})
            data = {'survey': survey, 'page': None, 'token': user_input.token}
            return request.render('survey.survey_init', data)
        # END Test mode

        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(survey, token=token)
        if errpage:
            return errpage

        # TODO: Check if user state already in survey line
        # Manual surveying
        user_input = UserInput.sudo().search([('survey_id', '=', survey.id), ('partner_id', '=', partner_id)], limit=1)
        if not user_input:
            vals = {'survey_id': survey.id}
            if not request.env.user._is_public():
                vals['partner_id'] = request.env.user.partner_id.id
            user_input = UserInput.create(vals)

        # Do not open expired survey
        errpage = self._check_deadline(user_input)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # Intro page
            data = {'survey': survey, 'page': None, 'token': user_input.token}
            return request.render('survey.survey_init', data)
        else:
            return request.redirect('/survey/fill/%s/%s' % (survey.id, user_input.token))
    
    @http.route()
    def submit(self, survey, **post):
        # Controls if the survey can be displayed
        if survey.stage_id.closed:
            return request.render("survey.notopen")
        return super(CustomSurvey, self).submit(survey)