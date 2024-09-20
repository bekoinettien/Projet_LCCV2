# -*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved

#
##############################################################################


from odoo import fields, models, api, exceptions
import math
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta

# class ordre_master(models.Model):
#     _name = 'payment.order'
#     _description = 'Etat Ordre de virement'
#
#     def draft_payslip_run(self):
#         for record in self:
#             if record.line_ids:
#                 record.line_ids.unlink()
#         return self.write({"state": 'draft'})
#
#     def action_done(self):
#         return self.write({"state": 'paid'})
#
#     @api.depends('line_ids.amount')
#     def _amount_all(self):
#         for p in self:
#             total = sum(line.amount for line in p.line_ids)
#             p.amount_total = total
#
#     def generate(self):
#         obj = self.env['payment.order.line']
#         for p in self:
#             res = self.env['planting.payslip.run'].search([('state', '=', 'close'), ('date_start', '>=', p.date_from), ('date_end', '<=', p.date_to)])
#             if not res:
#                 raise exceptions.ValidationError('Pas de Lot de paie pour cette periode')
#             if p.line_ids:
#                 p.line_ids.unlink()
#             for payslip in res.slip_ids:
#                 obj.create({
#                     'amount': payslip.amount_net,
#                     'partner_id': payslip.partner_id.id,
#                     'num': payslip.acc_number,
#                     'bank_id': payslip.bank_id.id,
#                     'date': p.date_from,
#                     'master_id': p.id
#                 })
#         return self.write({'state': 'confirmed'})
#
#     @api.model
#     def create(self, values):
#         values['name'] = self.env['ir.sequence'].next_by_code('payment.order')
#         return super(ordre_master, self).create(values)
#
#     name = fields.Char('Libelle', required=True, default="Ordre de virement")
#     company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
#     date_from = fields.Date(string='Date Debut', required=True, readonly=False, states={'draft': [('readonly', False)]}, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
#     date_to = fields.Date(string='Date Fin', required=True, readonly=False, states={'draft': [('readonly', False)]}, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
#     amount_total = fields.Float(compute="_amount_all", string='Montant Total', store=True, help='Montant total')
#     line_ids = fields.One2many('payment.order.line', 'master_id', 'Lignes de ordres de virement', readonly=True)
#     state = fields.Selection([
#         ('draft', 'Brouillon'),
#         ('confirmed', 'Confirme'),
#         ('paid', 'Termine')], 'Etat', readonly=True, default="draft")
class ordre_master(models.Model):
    _name = 'payment.order'
    _description = 'Etat Ordre de virement'

    def draft_payslip_run(self):
        for record in self :
            if record.line_ids :
                record.line_ids.unlink()
        return self.write({"state": 'draft'})

    def action_done(self):
        return self.write({"state": 'paid'})

    def _amount_all(self):
        for p in self:
            total = 0.0
            for line in p.line_ids:
                total = total + line.amount
            p.amount_total = total

    def generate(self):
        obj = self.env['payment.order.line']
        for p in self:
            res = self.env['planting.payslip.run'].search([('state','=','close'),('date_start','>=',p.date_from),('date_end','<=',p.date_to)])
            if not res:
                raise exceptions.ValidationError('Pas de Lot de paie pour cette periode')
            if p.line_ids:
                p.unlink()
            for payslip in res.slip_ids:
                obj.create({
                    'amount': payslip.amount_net,
                    'partner_id': payslip.partner_id.id,
                    'num': payslip.acc_number,
                    'bank_id': payslip.bank_id.id,
                    'date': p.date_from,
                    'master_id': p.id
                })
        return self.write({'state': 'confirmed'})

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('payment.order')
        return super(ordre_master, self).create(values)

    name = fields.Char('Libelle', required=True, default="Ordre de virement")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,default=lambda self: self.env.company)

    date_from = fields.Date(string='Date Debut', required=True, readonly=False,
                           states={'draft': [('readonly', False)]},
                           default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date(string='Date Fin', required=True, readonly=False, states={'draft': [('readonly', False)]},
                           default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    # myp_id = fields.Many2one('hr.payment.mode', 'Moyen de paiement', required=True)
    amount_total = fields.Float(compute="_amount_all", string='Montant Total', store=True, help='Montant total')
    line_ids = fields.One2many('payment.order.line', 'master_id', 'Lignes de ordres de virement', readonly=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirme'),
        ('paid', 'Termine')], 'Etat', readonly=True, default="draft")

    #MISE A JOUR 06/09/24
    # button_clicked = fields.Boolean(string='Bouton Cliqué', readonly=True, default=False)
    #
    #
    # def action_create_payment_order(self):
    #     """Créer un ordre de virement pour le lot de paie sélectionné."""
    #     for record in self:
    #         if record.state != 'confirmed':
    #             raise exceptions.UserError(
    #                 'Vous pouvez seulement créer un ordre de virement pour un état confirmé.')
    #
    #         # Crée un ordre de paiement pour chaque lot de paie confirmé
    #         payslip_runs = self.env['planting.payslip.run'].search([
    #             ('state', '=', 'close'),
    #             ('date_start', '=', record.date_from),
    #             ('date_end', '=', record.date_to)
    #         ])
    #
    #         if not payslip_runs:
    #             raise exceptions.UserError('Aucun lot de paie trouvé pour la période spécifiée.')
    #
    #         for payslip_run in payslip_runs:
    #             for payslip in payslip_run.slip_ids:
    #                 self.env['payment.order.line'].create({
    #                     'amount': payslip.amount_net,
    #                     'partner_id': payslip.partner_id.id,
    #                     'num': payslip.acc_number,
    #                     'bank_id': payslip.bank_id.id,
    #                     'date': record.date_from,
    #                     'master_id': record.id
    #                 })
    #
    #         # Mise à jour de l'état du bouton
    #         record.write({'state': 'paid', 'button_clicked': True})
    #
    #     return True
    # #FIN
class ordre_master_line(models.Model):
    _name = 'payment.order.line'
    _description = 'Lignes des Ordres de virement'

    partner_id = fields.Many2one('res.partner', string='Planteurs', readonly=True)
    bank_id = fields.Many2one('res.bank', string='Banque', readonly=True)
    ref = fields.Char('Matricule',related="partner_id.code_farmer")
    date = fields.Date('Date')
    num = fields.Char('Numero de compte',readonly=True)
    master_id = fields.Many2one('payment.order', 'Ordre de virement',readonly=True, required=True, ondelete='cascade')
    amount = fields.Float('Montant net', digits=(6, 2),readonly=True)
    myp_id = fields.Many2one('plantation.myp', string="Mode de paiement", related='partner_id.myp_id', readonly=True)



