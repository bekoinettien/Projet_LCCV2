#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models


class ReportPlanting(models.Model):
    _name = 'report.planting'
    _description = 'Rapport de sytnthse Achat'

    name = fields.Char(string="Libelle", required=False, default="Synthèse")
    total = fields.Monetary("Total Apromac", readonly=True,)
    total_qty = fields.Monetary("Total Quantité", readonly=True,)
    total_net = fields.Monetary("Total Net à payer", readonly=True,)
    date_start = fields.Date(string="Date Debut",readonly=True, required=True)
    date_end = fields.Date(string="Date Fin",readonly=True, required=True)
    bank_id = fields.Many2one('res.bank', string='Banque', readonly=True)
    type_id = fields.Many2one(comodel_name="type.farmer", readonly=True, string="Type Plantation", required=False)
    line_ids = fields.One2many(comodel_name="report.planting.line", inverse_name="report_id", string="Rapport")
    line_order_ids = fields.One2many(comodel_name="report.order.line", inverse_name="report_id", string="Rapport")
    type = fields.Selection(string='Type', selection=[('simple', 'Synthese'), ('global', 'Synthese Generale'),('order', 'Etat Paie'),  ],default="simple")
    company_id = fields.Many2one('res.company', string="Societé", default=lambda self: self.company_id)
    currency_id = fields.Many2one('res.currency', string="Devise", default=lambda self: self.env.company.currency_id)


class ReportPlantingLine(models.Model):
    _name = 'report.planting.line'
    _description = 'Ligne sytnthse Achat'

    ref = fields.Char(string="Reference", required=False, )
    number = fields.Char(string="Matricule", related="partner_id.code_farmer" ,required=False, )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Planteurs")
    report_id = fields.Many2one(comodel_name="report.planting", string="Rapport", required=True,ondelete="cascade" )
    qty = fields.Float(string="Qté",  required=False, )
    price = fields.Monetary(string="Prix affecté",  required=False, )
    amount = fields.Monetary(string="Montant Apromac",  required=False, )
    amount_net = fields.Monetary(string="Net à payer",  required=False,)
    type_id = fields.Many2one(comodel_name="type.farmer", readonly=True, string="Type Plantation", required=False)
    type = fields.Selection(string='Type',related="report_id.type")
    company_id = fields.Many2one('res.company', string="Societé", related="report_id.company_id")
    currency_id = fields.Many2one('res.currency', string="Devise", related="report_id.currency_id")




class ReportPOrderLine(models.Model):
    _name = 'report.order.line'
    _description = 'Ligne sytnthse Achat'

    partner_id = fields.Many2one('res.partner', string='Planteurs', readonly=True)
    bank_id = fields.Many2one('res.bank', string='Banque', readonly=True)
    ref = fields.Char('Matricule', related="partner_id.code_farmer")
    num = fields.Char('Numero de compte', readonly=True)
    report_id = fields.Many2one(comodel_name="report.planting", string="Rapport", required=True,ondelete="cascade" )
    amount = fields.Float('Montant net', digits=(6, 2), readonly=True)




