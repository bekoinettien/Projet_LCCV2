# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
import time, babel
from datetime import datetime,time
from odoo.tools import float_round
from odoo.tools.misc import format_date
from odoo import fields, models, api, exceptions, tools
import logging
_logger = logging.getLogger(__name__)



class planting_payslip_run(models.Model):
    _name = 'planting.payslip.run'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lot de fiche de paie plantation'

    @api.depends("slip_ids",'state')
    def _get_net(self):
        for p in self:
            total = 0
            for line in p.slip_ids:
                total += line.amount_net
            p.amount_net = total

    name = fields.Char('Libelle', required=False, readonly=False, states={'draft': [('readonly', False)]})
    slip_ids = fields.One2many('planting.payslip', 'payslip_run_id', 'Fiche de paie', required=False, readonly=True,
                               states={'draft': [('readonly', False)],'verifed': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('verifed', 'A verifier'),
        ('confirmed', 'Confirmé'),
        ('close', 'Fermé'),
        ('cancel', 'Annulé'),
    ], 'Statut', select=True, readonly=True, copy=False, tracking=True, default="draft")
    date_start = fields.Date('Du', required=True, readonly=False, states={'draft': [('readonly', False)]})
    date_end = fields.Date('Au', required=True, readonly=False, states={'draft': [('readonly', False)]})
    amount_net = fields.Float(compute="_get_net", store=True, string="Montant total a payer")
    company_id = fields.Many2one('res.company', 'Societé', required=True,default=lambda self: self.env.user.company_id.id)
    struct_id = fields.Many2one('planting.payroll.structure', domain=[('farmer','=',True)], string='Structure de facturation', required=False,readonly=False,
                               states={'draft': [('readonly', False)]})

    # AJOUTER CE CHAMPS LE 06/09.24
    payment_order_id = fields.Many2one('payment.order', string='Ordre de virement', readonly=True, copy=False)
    has_payment_order = fields.Boolean(string="Ordre de paiement créé", default=False)

    # controle_journal_id = fields.Many2one(
    #     'planting.account.move',
    #     string='Journal de Contrôle',
    #     help='Journal de contrôle associé à ce lot de paie.',
    #     readonly=True
    # )

   # planting_account_move_id = fields.Many2one('planting.account.move', string='Journal de control', readonly=True, copy=False)
    #ajouter 07/09/24



    @api.model
    def default_get(self, values):
        res = super(planting_payslip_run, self).default_get(values)
        if 'date_start' in values:
            ttyme = datetime.combine(fields.Date.from_string(datetime.now()), time.min)
            res['name'] = "Paie Planteur " + tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=self.env.context.get('lang')))
        return res

    @api.onchange('date_start','date_end')
    def onchange_date_start(self):
        for rec in self :
            if rec.date_start :
                ttyme = datetime.combine(fields.Date.from_string(rec.date_start), time.min)
                rec.name = "Paie Planteur " + tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=self.env.context.get('lang')))

    def unlink(self):
        for r in self:
            if r.state != "draft":
                raise exceptions.ValidationError("Vous ne pouvez pas supprimer un lot qui n'est pas l'étape brouillon")
            super(planting_payslip_run, self).unlink()

    def draft_payslip_run(self):
        for p in self:
            for l in p.slip_ids:
                l.draft_pesee()
        return self.write({'state': 'draft'})

    def cancel_payslip_run(self):
            for p in self:
                for l in p.slip_ids:
                    l.cancel_sheet()
            return self.write({'state': 'cancel'})


    def compute_sheet(self):
        for r in self:
            for l in r.slip_ids:
                l.compute_sheet()
        return True

    def close_payslip_run(self):
        for p in self:
            for l in p.slip_ids:
                l.close_pesee()
        return self.write({'state': 'close'})
    # def close_payslip_run(self, debit_account_id=None, debit=0.0, credit=0.0, line_type=None, name=False, number=0):
    #     for record in self:
    #         # Vérifier si un journal de contrôle existe déjà
    #         if not record.controle_journal_id:
    #             # Créer un nouveau journal de contrôle
    #             for slip in record.slip_ids:
    #                 journal = self.env['planting.account.move'].create({
    #                     'journal_code': "ACH_MP",
    #                     'payslip_date': record.create_date,
    #                     'invoice': slip.partner_id.code_farmer + "/" + slip.date_from.strftime(
    #                         '%d%m%Y') + "-" + slip.date_to.strftime('%d%m%Y'),
    #                     'ref': str(number),
    #                     'account_code': line_type == "C" and slip.partner_id.property_account_payable_id.code or debit_account_id and debit_account_id.code or '',
    #                     'partner_account': line_type == "C" and slip.partner_id.code_farmer or False,
    #                     'name': line_type == "C" and "ACHAT FONDS DE TASSE " + slip.partner_id.name + " " + slip.date_from.strftime(
    #                         '%d %m') + " au " + slip.date_to.strftime('%d %m %Y') or name,
    #                     'date_due': slip.date_from,
    #                     'debit': debit,
    #                     'credit': credit,
    #                     'analytic': line_type == "A" and "L0101000" or False,
    #                     'type': line_type == "C" and "G" or line_type,
    #                 })
    #                 # Lier le journal de contrôle au lot de paie
    #                 record.controle_journal_id = journal.id
    #
    #         # Fermer les fiches de paie associées
    #         for l in record.slip_ids:
    #             l.close_pesee()
    #
    #         # Appel de la méthode action_account_move
    #         for slip in record.slip_ids:
    #             slip.action_account_move()
    #
    #
    #     return self.write({'state': 'close'})

    def confirm_payslip_run(self):
        for p in self:
            for l in p.slip_ids:
                l.compute_sheet()
                l.write({'state': 'confirmed'})
        return self.write({'state': 'confirmed'})



#MISE A JOUR BEKOIN 06/09/24 DU BOTON VIRER
    def action_create_payment_order(self):
        """Créer un ordre de virement pour le lot de paie sélectionné."""
        payment_order_obj = self.env['payment.order']
        for record in self:
            if record.state != 'close':
                raise exceptions.UserError(
                    'Vous pouvez seulement créer un ordre de virement pour un lot de paie fermé.')

            if record.payment_order_id:
                raise exceptions.UserError('Un ordre de virement a déjà été créé pour ce lot de paie.')

            # Crée un ordre de paiement
            payment_order = payment_order_obj.create({
                'date_from': record.date_start,
                'date_to': record.date_end,
                'company_id': record.company_id.id,
            })

            # Remplit les lignes de l'ordre de paiement
            for payslip in record.slip_ids:
                self.env['payment.order.line'].create({
                    'amount': payslip.amount_net,
                    'partner_id': payslip.partner_id.id,
                    'num': payslip.acc_number,
                    'bank_id': payslip.bank_id.id,
                    'myp_id': payslip.myp_id.id,
                    'date': record.date_start,
                    'master_id': payment_order.id
                })

            # Lie l'ordre de paiement au lot de paie
            record.payment_order_id = payment_order.id

            # Change l'état de l'ordre de paiement
            payment_order.write({'state': 'confirmed'})
            # Change le statut pour indiquer que l'ordre de paiement a été créé
            # Marque l'ordre de paiement comme créé
            record.has_payment_order = True


        return True



class planting_payslip(models.Model):
    _name = 'planting.payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fiche de paye planteur'


    struct_id = fields.Many2one('planting.payroll.structure', 'Structure', readonly=False, states={'draft': [('readonly', False)]},
                                help='Defines the rules that have to be applied to this payslip, accordingly to the contract chosen. If you let empty the field contract, this field isn\'t mandatory anymore and thus the rules applied will be all the rules set on the structure of all contracts of the employee valid for the chosen period')
    name = fields.Char('Libelle', required=False, readonly=False, states={'draft': [('readonly', False)]})
    acc_number = fields.Char('Numero compte',readonly=True)

    number = fields.Char('Reference', required=False, readonly=False, states={'draft': [('readonly', False)]},
                         copy=False)
    partner_id = fields.Many2one('res.partner', 'Planteur', domain="[('farmer','=',True)]", readonly=False,states={'draft': [('readonly', False)]})
    code_farmer = fields.Char(string="Code Planteur", related='partner_id.code_farmer', store=True)

    bank_id = fields.Many2one('res.bank', 'Banque', readonly=True)
    myp_id = fields.Many2one('plantation.myp', string="Mode de paiement", related="partner_id.myp_id", readonly=True)

    #code_farmer = fields.Char(string= 'Banque', readonly=True)
    date_from = fields.Date('Date de debut', readonly=False, states={'draft': [('readonly', False)]}, required=True)
    date_to = fields.Date('Date de fin', readonly=False, states={'draft': [('readonly', False)]}, required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], 'Statut', select=True, readonly=True, copy=False,
        help='* Brouillon : la fiche est au brouillon.\
            \n* Confirmé : la fiche est validee par le responsable. \
            \n* If the payslip is confirmed then status is set to \'Done\'.\
            \n* When user cancel payslip the status is \'Rejected\'.', default="draft")
    line_ids = fields.One2many('planting.payslip.line', 'slip_id', 'Payslip Lines', readonly=False, states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Societe', required=False, readonly=False,
                                 states={'draft': [('readonly', False)]}, copy=False,default=lambda self: self.env.user.company_id.id)
    input_line_ids = fields.One2many('planting.payslip.input', 'payslip_id', 'Payslip Inputs', required=False,
                                     readonly=False, states={'draft': [('readonly', False)]},)
    line_pesee_ids = fields.One2many('planting.payslip.pesee', 'payslip_id', 'Pesees', required=False, readonly=False,
                                      states={'draft': [('readonly', False)]})
    paid = fields.Boolean('Payer?', required=False, readonly=False, states={'draft': [('readonly', False)]}, copy=False)

    note = fields.Text('Note Interne', readonly=False, states={'draft': [('readonly', False)]})

    payslip_run_id = fields.Many2one('planting.payslip.run', 'Lot de paie', readonly=False,states={'draft': [('readonly', False)]}, copy=False,ondelete='cascade')
    amount_pesee = fields.Float(string="Qte total",)
    #amount_pesee1 = fields.Float(string="Qte total NON EUDR",)
    amount_net = fields.Float(string="Total Net")
   # amount_net1 = fields.Float(string="Total Net NON EUDR")
    gains = fields.Float(string="Total gains")
   # gains1 = fields.Float(string="Total gains NON EUDR")
    returned = fields.Float(string="Total retenues")
    price = fields.Float(string="Prix du produit")
    prix_apromac = fields.Float(string="Prix Apromac")
   # < !--  ################ price1 10/09/24  ##############-->
   # price1 = fields.Float(string="Prix du produit NON EUDR")
    price_driver = fields.Float(string="Transport")
    prime = fields.Float(string="Prime EUDR")
    prime1 = fields.Float(string="Prime NON EUDR")
    quota= fields.Float(string="Quota")
    #prix_oct1= fields.Float(string="Prix 1")
    #journal_control_id = fields.Many2one('planting.journal.control', string="Journal de Contrôle")
   # account_move_ids = fields.One2many('planting.account.move', 'payslip_id', string='Mouvements Comptables')
    total_qty_eudr = fields.Float(string="Total Poids EUDR", compute='compute_sheet', store=True)
    total_qty_non_eudr = fields.Float(string="Total Poids NON EUDR", compute='compute_sheet', store=True)
    total_amount_eudr = fields.Float(string="Montant Total EUDR", compute='compute_sheet', store=True)
    total_amount_non_eudr = fields.Float(string="Montant Total NON EUDR", compute='compute_sheet', store=True)
    Total_poids = fields.Float(string='Total General livré')
    @api.depends('line_pesee_ids.qty', 'line_pesee_ids.origine')
    def _compute_totals(self):
        for record in self:
            total_eudr = 0.0
            total_non_eudr = 0.0
            for line in record.line_pesee_ids:
                if line.origine == 'EUDR':
                    total_eudr += line.qty
                elif line.origine == 'NON EUDR':
                    total_non_eudr += line.qty
            record.total_qty_eudr = total_eudr
            record.total_qty_non_eudr = total_non_eudr

    @api.constrains('date_from','date_to')
    def _check_dates(self):
        for payslip in self:
            if payslip.date_from > payslip.date_to:
                raise exceptions.ValidationError("La date de début doit être antérieure à la date de fin")
        return True

    def compute_line_pesee(self):
        for p in self:
            total = 0.0

            for line in p.line_pesee_ids:
                total = total + line.qty

            self.amount_pesee = total



    def unlink(self):
        for r in self:
            if r.state != "draft":
                raise exceptions.ValidationError("Vous ne pouvez pas supprimer une facture qui n'est pas l'etate brouillon")
        super(planting_payslip, self).unlink()

    def get_total_by_rule_category(self, code):
        """
        Return Cumul od Category
        :param code:
        :return:
        """
        category_total = 0.0

        for slip in self:
            for line in slip.line_ids.filtered(lambda x: x.code == code):
                category_total += line.total

        return category_total
    def create_account_move(self,debit_account_id,debit,credit,line_type,name=False, number=0):

        for record in self:
            self.env['planting.account.move'].create({
                'journal_code': "ACH_MP",
                'payslip_date': record.create_date,
                # 'invoice': record.partner_id.ref + "/" + record.date_from.strftime(
                #     '%d%m%Y') + "-" + record.date_to.strftime('%d%m%Y'),
                'invoice': record.partner_id.code_farmer + "/" + record.date_from.strftime(
                    '%d%m%Y') + "-" + record.date_to.strftime('%d%m%Y'),
                'ref': str(number),

                #KONAN - 29-12-2023: 'account_id': line_type == "C" and record.partner_id.property_account_payable_id.id or debit_account_id.id ,
                 'account_code': line_type == "C" and record.partner_id.property_account_payable_id.code or debit_account_id.code ,
                'partner_account': line_type == "C" and record.partner_id.code_farmer or False,
                'name': line_type == "C" and "ACHAT FONDS DE TASSE " + record.partner_id.name + " " + record.date_from.strftime(
                    '%d %m') + " au " + record.date_to.strftime('%d %m %Y') or name,
                'date_due': record.date_from,
                'debit': debit,
                'credit': credit,
                'analytic': line_type == "A" and "L0101000" or False,
                'type': line_type == "C" and "G" or line_type,


            })

    def action_account_move(self):
        debit_account = False
        config = self.env['config.payslip.planting'].search([], limit=1)
        for record in self:
            for line in record.line_ids.filtered(lambda x: x.salary_rule_id.debit_account_id):
                debit = line.total
                debit_account = line.salary_rule_id.debit_account_id
                record.create_account_move(debit_account,debit,0,"G",line.salary_rule_id.name,config.number)
                record.create_account_move(debit_account,debit,0,"A",line.salary_rule_id.name,config.number)
            record.create_account_move(debit_account,0,record.amount_net,"C","",config.number+1)
            config.number = config.number + 2
            # modification de code salary_rule_id en planting_salary_rule_id
    def close_pesee(self):
        for p in self:
            for l in p.line_pesee_ids:
                l.pesee_id.state = 'paid'
            p.gains = p.get_total_by_rule_category('TG')
            p.returned = p.get_total_by_rule_category('TR')
            p.action_account_move()


        return self.write({'state':'done','paid': True})

    def draft_pesee(self):
        for p in self:
            for l in p.line_pesee_ids:
                l.pesee_id.state = 'un_paid'
        return self.write({'state': 'draft'})

    def cancel_sheet(self):
        for p in self:
            for l in p.line_pesee_ids:
                l.pesee_id.state = 'un_paid'

        return self.write({'state': 'cancel'})

    def get_inputs(self):
        data = []
        old_input_ids = self.env['planting.payslip.input'].search([('payslip_id', '=', self.id)])
        if old_input_ids:
            old_input_ids.unlink()
        input_ids = self.env['planting.rule.input'].search([('farmer', '=', True)])
        if input_ids :
            for input in input_ids:
                lines = (0, 0, {
                    'name': input.name,
                    'code': input.code,
                })
                data.append(lines)

        return data
#MODIFICATION BEKOIN 10/09/24
    # @api.onchange('partner_id')
    # def onchange_partner(self):
    #     self.update({"line_pesee_ids": [(6, 0, [])]})
    #     data = []
    #     for rec in self:
    #         if not rec.partner_id:
    #             return
    #         if not rec.date_from:
    #             raise exceptions.ValidationError('Veuillez saisir une date de début!')
    #         if not rec.date_to:
    #             raise exceptions.ValidationError('Veuillez saisir une date de fin!')
    #
    #         # Obtenir les livraisons pour la période et le planteur
    #         res = self.env['farmer.pay'].search([
    #             ('date', '>=', rec.date_from),
    #             ('date', '<=', rec.date_to),
    #             ('farmer_id', '=', rec.partner_id.id)
    #         ])
    #
    #         if res:
    #             old_input_ids = self.env['planting.payslip.pesee'].search([('payslip_id', '=', rec.id)])
    #             if old_input_ids:
    #                 old_input_ids.unlink()
    #             for line in res:
    #                 farmer_id = line.id
    #                 lines = (0, 0, {
    #                     'name': line.name,
    #                     'qty': line.qty,
    #                     'origine': line.origine,  # Origine de la pesée
    #                     'date': line.date,
    #                     'pesee_id': farmer_id,
    #                     'product_id': line.product_id.id,
    #                 })
    #                 data.append(lines)
    #
    #     self.update({"line_pesee_ids": data})
    # MODIFICATION POUR LIER LA BANQUE A UN PLANTEUR BEKOIN 10/09/24
    @api.onchange('partner_id')
    def onchange_partner(self):
        self.update({"line_pesee_ids": [(6, 0, [])]})  # Réinitialisation des lignes de pesée
        data = []

        for rec in self:
            if not rec.partner_id:
                return
            if not rec.date_from:
                raise exceptions.ValidationError('Veuillez saisir une date de début!')
            if not rec.date_to:
                raise exceptions.ValidationError('Veuillez saisir une date de fin!')

            # Mise à jour des informations de banque et de compte bancaire
            if rec.partner_id.bank_ids:
                # Assurez-vous de sélectionner le premier compte bancaire disponible
                bank_account = rec.partner_id.bank_ids[0]
                rec.acc_number = bank_account.acc_number
                rec.bank_id = bank_account.bank_id.id

            # Obtenir les livraisons pour la période et le planteur
            res = self.env['farmer.pay'].search([
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('farmer_id', '=', rec.partner_id.id)
            ])

            if res:
                old_input_ids = self.env['planting.payslip.pesee'].search([('payslip_id', '=', rec.id)])
                if old_input_ids:
                    old_input_ids.unlink()
                for line in res:
                    farmer_id = line.id
                    lines = (0, 0, {
                        'name': line.name,
                        'qty': line.qty,
                        'origine': line.origine,  # Origine de la pesée
                        'date': line.date,
                        'pesee_id': farmer_id,
                        'product_id': line.product_id.id,
                    })
                    data.append(lines)

        self.update({"line_pesee_ids": data})

    # @api.onchange('partner_id')
    # def onchange_partner(self):
    #     self.update({"line_pesee_ids": [(6, 0, [])]})
    #     data = data_inputs = []
    #     for rec in self:
    #         if not rec.partner_id :
    #             return
    #         if not rec.date_from :
    #             raise exceptions.ValidationError('Veuillez sasir une date de début!')
    #         if not rec.date_to:
    #             raise exceptions.ValidationError('Veuillez sasir une date de fin!')
    #         data_inputs = rec.get_inputs()
    #         rec.struct_id = rec.partner_id.struct_id.id
    #         for bank in rec.partner_id.bank_ids:
    #             rec.acc_number = bank.acc_number
    #             rec.bank_id = bank.bank_id.id
    #         res = self.env['farmer.pay'].search([('date','>=',rec.date_from),('date','<=',rec.date_to),('farmer_id','=', rec.partner_id.id)])
    #         if res:
    #             old_input_ids = self.env['planting.payslip.pesee'].search([('payslip_id', '=', rec.id)])
    #             if old_input_ids:
    #                 old_input_ids.unlink()
    #             for line in res:
    #                 farmer_id = line.id
    #                 lines = (0, 0, {
    #                     'name': line.name,
    #                     'qty': line.qty,
    #
    #                     'date': line.date,
    #                     'pesee_id': farmer_id,
    #                     'product_id': line.product_id.id,
    #                 })
    #                 data.append(lines)
    #
    #     self.update({"line_pesee_ids": data,"input_line_ids":data_inputs})
    #

    def _get_base_local_dict(self):
        return {
            'float_round': float_round
        }




    def _get_payslip_lines(self):
        def _sum_salary_rule_category(localdict, category, amount):
            localdict['categories'].dict[category.code] = localdict['categories'].dict.get(category.code, 0) + amount
            return localdict

        self.ensure_one()
        result = {}
        rules_dict = {}
        inputs_dict = {line.code: line for line in self.input_line_ids if line.code}
        config = self.env['config.payslip.planting'].search([],limit=1)
        partner_id = self.partner_id.id

        class BrowsableObject(object):
            def __init__(self, farmer, dict, env):
                self.farmer_id = farmer
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                        SELECT sum(amount) as sum
                        FROM planting_payslip as hp, planting_payslip_input as pi
                        WHERE hp.partner_id = %s AND hp.state = 'done'
                        AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",(self.farmer_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                        to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                                FROM planting_payslip as hp, planting_payslip_line as pl
                                WHERE hp.partner_id = %s AND hp.state = 'done'
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                                        (self.farmer_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

            def sum_category(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()

                self.env['planting.payslip'].flush(['credit_note', 'partner_id', 'state', 'date_from', 'date_to'])
                self.env['planting.payslip.line'].flush(['total', 'slip_id', 'category_id'])
                self.env['planting.salary.rule.category'].flush(['code'])

                self.env.cr.execute("""SELECT sum(case when hp.credit_note is not True then (pl.total) else (-pl.total) end)
                                FROM planting_payslip as hp, planting_payslip_line as pl, planting_rule_category as rc
                                WHERE hp.partner_id = %s AND hp.state = 'done'
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id
                                AND rc.id = pl.category_id AND rc.code = %s""",
                                        (self.farmer_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0
        localdict = {
                **self._get_base_local_dict(),
                **{
                    'categories': BrowsableObject(partner_id, {}, self.env),
                    'rules': BrowsableObject(partner_id, rules_dict, self.env),
                    'payslip': Payslips(partner_id, self, self.env),
                    'inputs': InputLine(partner_id, inputs_dict, self.env),
                    'config': config,
                }
        }
        for rule in sorted(self.struct_id.rule_ids, key=lambda x: x.sequence):
            localdict.update({
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100})
            if rule.satisfy_condition(localdict):
                amount, qty, rate = rule.compute_rule(localdict)
                # check if there is already a rule computed with that code
                previous_amount = rule.code in localdict and localdict[rule.code]  or 0.0                # set/overwrite the amount computed for this rule in the localdict
                tot_rule = amount * qty * rate / 100.0
                #tot_rule1 = amount * qty1 * rate / 100.0
                localdict[rule.code] = tot_rule
                #localdict[rule.code1] = tot_rule1
                rules_dict[rule.code] = rule
                # rules_dict[rule.code1] = rule
                # sum the amount for its salary category
                localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                # create/overwrite the rule in the temporary results
                total = 0.0
                # total1 = 0.0
                if rule.code == 'NET':
                    total = total + float_round(tot_rule,precision_digits=2)
                    #total1 = total1 + float_round(tot_rule,precision_digits=2)
                self.write({'amount_net': total})
               # self.write({'amount_net1': total1})
                result[rule.code] = {
                    'sequence': rule.sequence,
                    'code': rule.code,
                    'name': rule.name,
                    'note': rule.note,
                    'salary_rule_id': rule.id,
                    'category_id': rule.category_id.id,
                    'partner_id': partner_id,
                    'amount': amount,
                    'quantity': qty,
                    'rate': rate,
                    'appears_on_payslip': rule.appears_on_payslip,
                    'condition_select': rule.condition_select,
                    'condition_python': rule.condition_python,
                    'condition_range': rule.condition_range,
                    'condition_range_min': rule.condition_range_min,
                    'condition_range_max': rule.condition_range_max,
                    'amount_select': rule.amount_select,
                    'amount_fix': rule.amount_fix,
                    'amount_python_compute': rule.amount_python_compute,
                    'amount_percentage': rule.amount_percentage,
                    'amount_percentage_base': rule.amount_percentage_base,
                    # 'register_id': rule.register_id.id,
                    'slip_id': self.id,
                    'total': float_round(amount * qty * rate / 100.0,precision_digits=2)

                }
        return result.values()

####gestion des quantité en eudr et non eudr 10/09/24 BEKOIN
    def compute_sheet(self):
        sequence_obj = self.env['ir.sequence']

        for payslip in self:
            if not payslip.partner_id.group_id:
                raise exceptions.ValidationError('Le planteur n\'est associé à aucun groupe !')
            # Récupérer le prix le plus récent pour le groupe de planteur
            res_price = self.env['planting.pricing.line'].search([
                ('group_id', '=', payslip.partner_id.group_id.id)
            ], limit=1, order="date desc")
            _logger.info("Tous les prix pour le groupe %s : %s", payslip.partner_id.group_id.name, res_price)

            if not res_price:
                raise exceptions.ValidationError(
                    'Aucun prix trouvé pour le groupe de planteur %s' % (payslip.partner_id.group_id.name))

            # Mettre à jour les prix de la fiche de paie
            payslip.update({
                'price': res_price.price or 0.0,  # Prix pour EUDR
                'prix_apromac': res_price.prix_apromac or 0.0,  # Prix APROMAC
               # 'price1': res_price.price1 or 0.0,  # Prix pour NON EUDR
                'price_driver': res_price.price_driver or 0.0,
                'prime': res_price.prime or 0.0,
                'prime1': res_price.prime1 or 0.0
            })

            # Générer le numéro et le nom de la fiche de paie
            payslip.number = payslip.number or sequence_obj.next_by_code('farmer.slip')
            payslip.name = ('Fiche de paie %s pour %s') % (
                payslip.partner_id.name,
                format_date(self.env, payslip.date_from, date_format="MMMM y")
            )

            # Calculer les totaux pour EUDR et NON EUDR
            total_qty_eudr = 0.0
            total_qty_non_eudr = 0.0
            total_amount_eudr = 0.0
            total_amount_non_eudr = 0.0

            for line in payslip.line_pesee_ids:
                if line.origine == 'EUDR':
                    total_qty_eudr += line.qty
                    total_amount_eudr += line.qty * payslip.price  # Calculer montant pour EUDR
                elif line.origine == 'NON EUDR':
                    total_qty_non_eudr += line.qty
                    total_amount_non_eudr += line.qty * payslip.price  # Calculer montant pour NON EUDR
                   # total_amount_non_eudr += line.qty * payslip.price1  # Calculer montant pour NON EUDR

            # Supprimer les anciennes lignes de paie et ajouter les nouvelles
            if payslip.line_ids:
                payslip.line_ids.unlink()
            reslut = payslip.prime * payslip.total_qty_eudr
            result1 = payslip.prime1 * payslip.total_qty_non_eudr
            TotalPoids = total_qty_eudr + total_qty_non_eudr
            resultTransport = payslip.price_driver * payslip.Total_poids
            payslip.write({
                'line_ids': [(0, 0, line) for line in payslip._get_payslip_lines()],
                'total_qty_eudr': total_qty_eudr,
                'total_qty_non_eudr': total_qty_non_eudr,
                'Total_poids': TotalPoids,
                'total_amount_eudr': total_amount_eudr,  # Montant total pour EUDR
                'total_amount_non_eudr': total_amount_non_eudr,  # Montant total pour NON EUDR
                'amount_net': (total_amount_eudr + total_amount_non_eudr + reslut+result1)-resultTransport,
            })

        return True

    # def compute_sheet(self):
    #
    #     sequence_obj = self.env['ir.sequence']
    #
    #     for payslip in self:
    #         res_price = self.env['planting.pricing.line'].search([('group_id', '=',payslip.partner_id.group_id.id)], limit=1, order="date desc")
    #         if not res_price :
    #             raise exceptions.ValidationError('Aucun prix trouvé pour le groupe de planteur %s'%(payslip.partner_id.group_id.name))
    #         payslip.price = res_price and res_price.price or 0.0
    #         payslip.price1 = res_price and res_price.price1 or 0.0
    #         payslip.price_driver = res_price and res_price.price_driver or 0.0
    #         payslip.prime = res_price and res_price.prime or 0.0
    #         number = payslip.number or sequence_obj.next_by_code('farmer.slip')
    #         name = ('Fiche de paie %s pour %s') % (payslip.partner_id.name, format_date(self.env, payslip.date_from, date_format="MMMM y"))
    #
    #         # delete old payslip lines
    #         total = sum(line.qty for line in payslip.line_pesee_ids)
    #         if payslip.line_ids:
    #             payslip.line_ids.unlink()
    #         lines = [(0, 0, line) for line in payslip._get_payslip_lines()]
    #         payslip.write({'line_ids': lines, 'number': number, 'name': name,'amount_pesee':total})
    #     return True


class hr_payslip_input(models.Model):
    '''
    Payslip Input
    '''

    _name = 'planting.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char('Description', required=True)
    payslip_id = fields.Many2one('planting.payslip', 'Pay Slip', required=True, ondelete='cascade', select=True)
    sequence =  fields.Integer('Sequence', required=True, select=True,default=10)
    code =  fields.Char('Code', required=True, help="The code that can be used in the salary rules")
    amount =  fields.Float('Montant',help="It is used in computation. For e.g. A rule for sales having 1% commission of basic salary for per product can defined in expression like result = inputs.SALEURO.amount * contract.wage*0.01.")
    # partner_id =  fields.Many2one('res.partner', 'Planteur/Transporteur',help="The contract for which applied this input")





class planting_payslip_pesee(models.Model):
    '''
    Payslip Input
    '''

    _name = 'planting.payslip.pesee'
    _description = 'Pesees de la paie'
    _order = 'payslip_id, sequence'

    name = fields.Char('Numero de ticket', required=True)
    payslip_id = fields.Many2one('planting.payslip', 'Fiche de paie', required=True, ondelete='cascade',)
    pesee_id = fields.Many2one('farmer.pay', 'Fiche Planteurs à payer')
    date = fields.Date(string='Date',required=False)
    sequence = fields.Integer('Sequence', required=False, select=True)
    qty = fields.Float('Qte', help="Quantite ")
   # qty1 = fields.Float('Qte NON EUDR', help="Quantite NON EUDR")
    product_id = fields.Many2one('product.template', 'Produit', required=True)
    origine = fields.Char('Origine', required=True)
    total_qty_eudr = fields.Float(string="Total Poids EUDR", compute='_compute_totals', store=True)
    total_qty_non_eudr = fields.Float(string="Total Poids NON EUDR", compute='_compute_totals', store=True)

    @api.depends('qty', 'origine')
    def _compute_totals(self):
        for rec in self:
            rec.total_qty_eudr = sum(line.qty for line in rec if line.origine == 'EUDR')
            rec.total_qty_non_eudr = sum(line.qty for line in rec if line.origine == 'NON EUDR')




class hr_payslip_line(models.Model):
    '''
    Payslip Line
    '''

    _name = 'planting.payslip.line'
    _inherit = 'planting.salary.rule'
    _description = 'Payslip Line'
    _order = 'partner_id, sequence'

    def _calculate_total(self):
        if not self._ids: return {}
        for line in self:
            self.total = float_round(float(line.quantity) * line.amount * line.rate / 100)

    slip_id = fields.Many2one('planting.payslip', 'Pay Slip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('planting.salary.rule', 'Rule', required=True)
    partner_id = fields.Many2one('res.partner', 'Planteur/Transporteur', required=True)
    rate = fields.Float('Taux (%)', digits=(6,2),default=100)
    amount = fields.Float('Montant', digits=(6,2))
    quantity = fields.Float('Quantité', digits=(6,2),default=1)
    total = fields.Float(string='Total',compute="_calculate_total", method=True,digits=(6,2), store=True)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
