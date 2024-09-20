    # -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
##############################################################################

from odoo import fields, models,api,exceptions
import base64
import os
import time
from odoo.exceptions import UserError


class Weight(models.Model):
    _name = 'weight.weight'
    _description = 'Weight'

    name = fields.Char("Ticket pesée", required=True,readonly=False)
    carrier = fields.Char("N° de Vehicule",readonly=False)
    driver = fields.Char("Chauffeur",readonly=False)
    first_weigher = fields.Char("Peseur",readonly=False)
    code_product = fields.Char(string='Code produit',default="1", required=False)
    code_farmer = fields.Char(string='Matricule planteur', required=False)
    locality = fields.Char(string='Région', required=False)
    sector = fields.Char(string='Département', required=False)
    village = fields.Char(string='Village', required=False)
    date = fields.Date(string='Date livraison', required=False,readonly=False,default=lambda *a: time.strftime('%Y-%m-%d'))
    supplier_id = fields.Many2one(comodel_name='res.partner',string='Planteurs',required=False,readonly=True)
    product_id = fields.Many2one(comodel_name='product.template',string='Article',required=False,readonly=True)
    weigth_1 = fields.Float(string='Pesée 1')
    weigth_2 = fields.Float(string='Pesée 2')
    qty = fields.Float(string='Poids Net ', required=False)
    origine = fields.Char(string='Origine')
    aire = fields.Char(string="Emplaclement")
    weigth_supplier = fields.Float(string='Poids du Fournisseur')
    state = fields.Selection(string='Etat',selection=[('draft', 'Brouillon'),('done', 'Valider')], required=False, default="draft",readonly=True)
    #paiement_id = fields.Many2one(comodel_name='paiement.paiement', string='Paiement', required=True, ondelete='cascade')


    def unlink(self):
        for r in self:
            if r.state != "draft":
                raise exceptions.ValidationError("Vous ne pouvez pas supprimer une pesée qui n'est pas l'étape brouillon")
        super().unlink()

    def cancel(self):
        return self.write({'state':'draft'})


    def find_partner(self, supplier,product):
        supplier_id = self.env['res.partner'].search([('code_farmer', '=', supplier)], limit=1)
        product_id = self.env['product.template'].search([('code', '=',product)],limit=1)
        if not supplier_id:
            raise exceptions.UserError("Le code Planteur [%s]  n'existe pas !" % (supplier))
        if not product_id :
            raise exceptions.UserError("Le code produit [%s]  n'existe pas !" % (product))

        return supplier_id.id,product_id.id

    def action_confirm(self):
        res = self.search([('state', '=', 'draft')])
        for rec in res :
            partner = self.find_partner(rec.code_farmer,rec.code_product)
            rec.supplier_id = partner[0]
            rec.product_id = partner[1]
            self.env['farmer.pay'].create({
                'name': rec.name,
                'date': rec.date,
                'farmer_id': partner[0],
                'product_id': partner[1],
                'qty': rec.qty,
                'origine': rec.origine,
                'aire': rec.aire,
                #'qty1': rec.qty1
            })
            rec.write({'state': 'done'})
        return {"view_mode": 'tree,form', 'name': 'Planteur à payer',
                'res_model': 'farmer.pay', 'type': 'ir.actions.act_window', }


class FarmerPay(models.Model):

    _name = 'farmer.pay'
    _description = 'Verification des planteurs à payer'

    name = fields.Char('Numero de ticket', size=20, required=True, readonly=True)
    farmer_id = fields.Many2one('res.partner', 'Planteur', required=False, readonly=True)
    product_id = fields.Many2one('product.template','Produit', required=False, readonly=True)
    qty = fields.Float(string='Poids', required=True, readonly=True)
   # qty1 = fields.Float(string='Poids NON EUDR', required=True, readonly=True)
    date = fields.Date(string='Date', required=False, readonly=True)
    origine = fields.Char(string='Origine')
    aire = fields.Char(string="Emplaclement")
    state = fields.Selection(string='Statut', selection=[('un_paid', 'Non Payé'), ('paid', 'Payé')], default="un_paid", required=False, readonly=True)

class PrimeExceptionnelle(models.Model):
    _name = 'prime.exceptionnelle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherit = 'weight.weight'
    activate = fields.Boolean('Activation', default=True,)
    name = fields.Char("Libelle", default=" Prime Exceptionnelle", required=True)
    start_date = fields.Date("Date de Début")
    end_date = fields.Date("Date de Fin")
    seuil = fields.Integer('Seuil')
    prix1 = fields.Integer('Pix N°1')
    prix2 = fields.Integer('Pix N°2')
    Prime = fields.Integer('Prime Exceptionnelle')
    weight_ids = fields.Many2many("weight.weight", string="pesee")

    @api.onchange('seuil')
    def _onchange_seuil(self):
        # Mise à jour du champ weight_ids selon le seuil
        if self.seuil:
            self.weight_ids = self.env['weight.weight'].search([('qty', '>=', self.seuil)])

    def get_planteurs_with_seuil(self):
        # Obtenir les planteurs dont le poids net est supérieur ou égal au seuil
        planteurs = self.env['weight.weight'].search([('qty', '>=', self.seuil)])
        return planteurs
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError

class Prime(models.Model):
    _name = 'prime.prime'

    name = fields.Char('Groupe', required=True)
    seuil = fields.Integer('Seuil', required=True)
    price1 = fields.Integer('Prix N°1', required=True)
    price2 = fields.Integer('Prix N°2', required=True)
    farmer_ids = fields.Many2many("res.partner", string="Planteurs", required=False)
    line_selection_ids = fields.One2many(comodel_name='selection.selection', inverse_name='prime_id', tracking=True,
                                         string='Ligne de prix')

    @api.constrains('farmer_ids')
    def _check_unique_farmers(self):
        for record in self:
            for partner in record.farmer_ids:
                if partner.prime_id and partner.prime_id != record.id:
                    raise exceptions.ValidationError(
                        f"Le planteur {partner.name} est déjà associé au groupe {partner.prime_id.name}.")

    @api.model
    def create(self, vals):
        record = super(Prime, self).create(vals)
        record._update_partner_prime()
        return record

    def write(self, vals):
        result = super(Prime, self).write(vals)
        self._update_partner_prime()
        return result

    def _update_partner_prime(self):
        for partner in self.farmer_ids:
            partner.prime_id = self.id
        all_partners = self.env['res.partner'].search([('prime_id', '=', self.id)])
        for partner in all_partners:
            if partner not in self.farmer_ids:
                partner.prime_id = False


class Selection(models.Model):
    _name = 'selection.selection'

    active = fields.Boolean(string='Activation', default=False)
    name = fields.Char(string='Période de prime', required=True)
    datedebut = fields.Date(string='Date de début', required=True)
    datefin = fields.Date(string='Date de fin', required=True)
    prime_id = fields.Many2one(comodel_name='prime.prime', string='Sélectionner le groupe', required=False)

    _sql_constraints = [
        ('date_check', 'CHECK (datedebut <= datefin)',
         "La date de début doit être antérieure ou égale à la date de fin."),
        ('unique_period', 'UNIQUE (prime_id, datedebut, datefin)',
         "Une période pour un groupe ne peut pas se chevaucher avec une autre.")
    ]

    @api.model
    def default_get(self, fields_list):
        res = super(Selection, self).default_get(fields_list)
        if 'datedebut' in fields_list and 'datefin' in fields_list:
            res['name'] = f"Période de prime du {res.get('datedebut')} au {res.get('datefin')}"
        return res

    @api.onchange('datedebut', 'datefin')
    def _onchange_dates(self):
        if self.datedebut and self.datefin:
            self.name = f"Période de prime du {self.datedebut.strftime('%d/%m/%Y')} au {self.datefin.strftime('%d/%m/%Y')}"


class Paiement(models.Model):
    _name = 'paiement.paiement'
    _description = 'Paiement des Planteurs'

    # name = fields.Char(string="Référence", required=True)
    name = fields.Char(string="Référence", required=False, default=lambda self: self.env['ir.sequence'].next_by_code('paiement.reference'))
    group_id = fields.Many2one('prime.prime', string="Groupe", required=True)
    date_from = fields.Date(string="Date Début", required=True)
    date_to = fields.Date(string="Date Fin", required=True)
    payment_line_ids = fields.One2many('payment.line', 'payment_id', string="Lignes de Paiement")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé')
    ], string='État', default='draft')


    def action_pay(self):
        self.write({'state': 'paid'})
        # Copier les lignes de paiement validées dans une autre vue liste
        validated_payment_model = self.env['validated.payment']

        for line in self.payment_line_ids:
            validated_payment_model.create({
                'payment_id': self.id,
                'farmer_id': line.farmer_id.id,
                'total_weight': line.total_weight,
                'price': line.price,
                'amount': line.amount,
                'bank_id': line.bank_id,
                'myp_id': line.myp_id,
                'acc_number': line.acc_number,
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})


    @api.model
    def create(self, vals):
        existing_payment = self.env['paiement.paiement'].search([
            ('group_id', '=', vals.get('group_id')),
            ('date_from', '<=', vals.get('date_to')),
            ('date_to', '>=', vals.get('date_from'))
        ], limit=1)

        if existing_payment:
            raise UserError("Le groupe a déjà été payé pour cette période.")


        return super(Paiement, self).create(vals)

    @api.onchange('group_id', 'date_from', 'date_to')
    def _compute_payment_lines(self):
        if self.group_id and self.date_from and self.date_to:
            selections = self.env['selection.selection'].search([
                ('prime_id', '=', self.group_id.id),
                ('datedebut', '<=', self.date_to),
                ('datefin', '>=', self.date_from),
                ('active', '=', True)
            ])

            if not selections:
                raise UserError("Aucune prime active trouvée pour le groupe à cette période.")

            payment_lines = []
            for farmer in self.group_id.farmer_ids:
                total_weight = sum(self.env['weight.weight'].search([
                    ('supplier_id', '=', farmer.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to)
                ]).mapped('qty'))

                prime = 0
                if total_weight == self.group_id.seuil:
                    prime = total_weight * self.group_id.price1
                elif total_weight > self.group_id.seuil:
                    prime = (self.group_id.seuil * self.group_id.price1) + \
                            ((total_weight - self.group_id.seuil) * self.group_id.price2)

                if prime > 0:
                    payment_lines.append((0, 0, {
                        'farmer_id': farmer.id,
                        'total_weight': total_weight,
                        'price': prime,
                        'amount': prime  # La prime calculée
                    }))
            self.payment_line_ids = payment_lines


class PaymentLine(models.Model):
    _name = 'payment.line'
    _description = 'Ligne de Paiement'

    payment_id = fields.Many2one('paiement.paiement', string="Référence de Paiement", required=True)
    farmer_id = fields.Many2one('res.partner', string="Planteur", domain="[('farmer','=',True)]", required=True)
    code_farmer= fields.Char(string="Matricule Planteur", related='farmer_id.code_farmer', required=True)
    total_weight = fields.Float(string="Total Pesé", required=True)
    price = fields.Float(string="Prix", required=False)
    amount = fields.Float(string="Prime Exceptionnelle", compute="_compute_amount", store=True)
    bank_id = fields.Many2one('res.bank', 'Banque', readonly=True)
    myp_id = fields.Many2one('plantation.myp', string="Mode de paiement", related="farmer_id.myp_id", readonly=True)
    acc_number = fields.Char('Numero compte', readonly=True)

    @api.depends('total_weight', 'payment_id.group_id.seuil', 'payment_id.group_id.price1', 'payment_id.group_id.price2')
    def _compute_amount(self):
        for line in self:
            seuil = line.payment_id.group_id.seuil
            price1 = line.payment_id.group_id.price1
            price2 = line.payment_id.group_id.price2
            total_weight = line.total_weight

            if total_weight == seuil:
                line.amount = total_weight * price1
            elif total_weight > seuil:
                line.amount = (seuil * price1) + ((total_weight - seuil) * price2)
            else:
               continue  # Si le poids est inférieur au seuil, aucune prime n'est appliquée.

    @api.onchange('farmer_id')
    def onchange_partner(self):
        for ligne in self:
            #if ligne.farmer_id.bank_ids:
                # Assurez-vous de sélectionner le premier compte bancaire disponible
                bank_account = ligne.farmer_id.bank_ids[:1]
                ligne.acc_number = bank_account.acc_number
                ligne.bank_id = bank_account.bank_id.id


class ValidatedPayment(models.Model):
    _name = 'validated.payment'
    _description = 'Paiements Validés'

    name = fields.Char(string="Nom", required=True, default=lambda self: _('Nouveau'))
    payment_id = fields.Many2one('paiement.paiement', string="Paiement", required=True)
    farmer_id = fields.Many2one('res.partner', string="Planteur", domain="[('farmer','=',True)]", required=True)
    code_farmer= fields.Char(string="Matricule Planteur", related='farmer_id.code_farmer', required=True)
    total_weight = fields.Float(string="Poids Total", required=True)
    price = fields.Float(string="Prix", required=True)
    amount = fields.Float(string="Montant", required=True)
    bank_id = fields.Many2one('res.bank', 'Banque', readonly=True)
    myp_id = fields.Many2one('plantation.myp', string="Mode de paiement", related="farmer_id.myp_id", readonly=True)
    acc_number = fields.Char('Numero compte', readonly=True)

    # groupe de prime exceptionnelle
# class Prime(models.Model):
#
#     _name ='prime.prime'
#
#     name = fields.Char('Groupe', required=True)
#     seuil = fields.Integer('Seuil' ,required=True)
#     price1 = fields.Integer('Pix N°1',required=True)
#     price2 = fields.Integer('Pix N°2',required=True)
#     farmer_ids = fields.Many2many("res.partner",string="Planteurs", required=False,)
#     line_selection_ids = fields.One2many(comodel_name='selection.selection', inverse_name='prime_id', tracking=True,
#                                      string='Ligne de prix')
#
#     @api.constrains('farmer_ids')
#     def _check_unique_farmers(self):
#         for record in self:
#             # Vérifier si des planteurs de ce groupe sont présents dans un autre groupe
#             for partner in record.farmer_ids:
#                 if partner.prime_id and partner.prime_id != record.id:
#                     raise exceptions.ValidationError(
#                         f"Le planteur {partner.name} est déjà associé au groupe {partner.prime_id.name}.")
#
#     @api.model
#     def create(self, vals):
#         record = super(Prime, self).create(vals)
#         record._update_partner_prime()
#         return record
#
#     def write(self, vals):
#         result = super(Prime, self).write(vals)
#         self._update_partner_prime()
#         return result
#
#     def _update_partner_prime(self):
#         # Mettre à jour le champ prime_id pour les planteurs dans ce groupe
#         for partner in self.farmer_ids:
#             partner.prime_id = self.id
#         # Réinitialiser le champ prime_id des planteurs qui ne sont plus dans ce groupe
#         all_partners = self.env['res.partner'].search([('prime_id', '=', self.id)])
#         for partner in all_partners:
#             if partner not in self.farmer_ids:
#                 partner.prime_id = False
#  # gestion des selections des date et activation de prime exceptionnelle
#
# class Selection(models.Model):
#     _name = 'selection.selection'
#
#     active = fields.Boolean(string='Activation', default=False)
#     name = fields.Char(string='Période de prime', required=True)
#     datedebut = fields.Date(string='Date de début', required=True)
#     datefin = fields.Date(string='Date de fin', required=True)
#     prime_id = fields.Many2one(comodel_name='prime.prime',string='Selectionner le groupe ',required=False)
#     _sql_constraints = [
#         ('date_check', 'CHECK (datedebut <= datefin)',
#          "La date de début doit être antérieure ou égale à la date de fin."),
#         ('unique_period', 'UNIQUE (prime_id, datedebut, datefin)',
#          "Une période pour un groupe ne peut pas se chevaucher avec une autre.")
#     ]
#     # Garantit qu'une période de prime pour un groupe donné ne peut pas se
#     #            chevaucher avec une autre période pour le même groupe. Cette contrainte empêche
#     #            la duplication des périodes pour un même groupe
#     @api.model
#     def default_get(self, fields_list):
#         res = super(Selection, self).default_get(fields_list)
#         if 'datedebut' in fields_list and 'datefin' in fields_list:
#             res['name'] = f"Période de prime du {res.get('datedebut')} au {res.get('datefin')}"
#         return res
#
#     @api.onchange('datedebut', 'datefin')
#     def _onchange_dates(self):
#         if self.datedebut and self.datefin:
#             self.name = f"Période de prime du {self.datedebut.strftime('%d/%m/%Y')} au {self.datefin.strftime('%d/%m/%Y')}"
#
#
#
# class Paiement(models.Model):
#         _name = 'paiement.paiement'
#         _description = 'Paiement des Planteurs'
#
#         name = fields.Char(string="Reference", required=True)
#         group_id = fields.Many2one('prime.prime', string="Groupe", required=True)
#         date_from = fields.Date(string=" Date Debut", required=True)
#         date_to = fields.Date(string="Date Fin", required=True)
#         payment_line_ids = fields.One2many('payment.line', 'payment_id', string="Payment Lines")
#         state = fields.Selection([
#             ('draft', 'Brouillon'),
#             ('paid', 'Payé'),
#             ('cancelled', 'Annulé')
#         ], string='État', default='draft')
#
#         def action_pay(self):
#             self.write({'state': 'paid'})
#
#         def action_cancel(self):
#             self.write({'state': 'cancelled'})
#
#         def action_draft(self):
#             self.write({'state': 'draft'})
#
#         @api.model
#         def create(self, vals):
#             existing_payment = self.env['paiement.paiement'].search([
#                 ('group_id', '=', vals.get('group_id')),
#                 ('date_from', '<=', vals.get('date_to')),
#                 ('date_to', '>=', vals.get('date_from'))
#             ], limit=1)
#
#             if existing_payment:
#                 raise UserError("Le groupe a déjà été payé pour cette période.")
#
#             return super(Paiement, self).create(vals)
#
#         @api.onchange('group_id', 'date_from', 'date_to')
#         def _compute_payment_lines(self):
#             if self.group_id and self.date_from and self.date_to:
#                 selections = self.env['selection.selection'].search([
#                     ('prime_id', '=', self.group_id.id),
#                     ('datedebut', '<=', self.date_to),
#                     ('datefin', '>=', self.date_from),
#                     ('active', '=', True)
#                 ])
#
#                 if not selections:
#                     raise UserError("Aucune prime active trouvée pour le groupe à cette période.")
#
#                 payment_lines = []
#                 for farmer in self.group_id.farmer_ids:
#                     total_weight = sum(self.env['weight.weight'].search([
#                         ('supplier_id', '=', farmer.id),
#                         ('date', '>=', self.date_from),
#                         ('date', '<=', self.date_to)
#                     ]).mapped('qty'))
#
#                     if total_weight == self.group_id.seuil:
#                         price = self.group_id.price1
#                     elif total_weight > self.group_id.seuil:
#                         price = self.group_id.price2
#                     else:
#                         continue
#
#                     payment_lines.append((0, 0, {
#                         'farmer_id': farmer.id,
#                         'total_weight': total_weight,
#                         'price': price,
#                     }))
#                 self.payment_line_ids = payment_lines
#
#
#
#
# class PaymentLine(models.Model):
#
#     _name = 'payment.line'
#     _description = 'Payment Line'
#
#     payment_id = fields.Many2one('paiement.paiement', string="Payment Reference", required=True)
#     farmer_id = fields.Many2one('res.partner', string="Farmer", required=True)
#     total_weight = fields.Float(string="Total Pesé", required=True)
#     price = fields.Float(string="Prix", required=True)
#     amount = fields.Float(string="Prme Exceptionnelle", compute="_compute_amount", store=True)
#
#     @api.depends('total_weight', 'price')
#     def _compute_amount(self):
#         for line in self:
#             line.amount = line.total_weight * line.price
#

# *********************************************************************************
# paiement prime exceptionnelle
# class Paiement(models.Model):
#
#         _name = 'paiement.paiement'
#         _description = 'Paiement des Planteurs'
#         name = fields.Char(string="Reference", required=True)
#         group_id = fields.Many2one('prime.prime', string="Groupe", required=True)
#         date_from = fields.Date(string=" Date Debut", required=True)
#         date_to = fields.Date(string="Date Fin", required=True)
#         payment_line_ids = fields.One2many('payment.line', 'payment_id', string="Payment Lines")
#
#         @api.onchange('group_id', 'date_from', 'date_to')
#         def _compute_payment_lines(self):
#             if self.group_id and self.date_from and self.date_to:
#                 # farmers = self.group_id.farmer_ids
#                 # Récupère les périodes de prime associées au groupe
#                 selections = self.env['selection.selection'].search([
#                     ('prime_id', '=', self.group_id.id),
#                     ('datedebut', '<=', self.date_to),
#                     ('datefin', '>=', self.date_from),
#                     ('active', '=', True)
#                 ])
#
#                 if not selections:
#                     raise UserError("Aucune prime activer trouvée pour le groupe à cette dates spécifiées.")
#
#                 payment_lines = []
#                 for selection in selections:
#                     farmers = self.group_id.farmer_ids
#                 for farmer in farmers:
#                     # Calcul du total des pesées pour la période spécifiée
#                     total_weight = sum(self.env['weight.weight'].search([
#                         ('supplier_id', '=', farmer.id),
#                         ('date', '>=', self.date_from),
#                         ('date', '<=', self.date_to)
#                     ]).mapped('qty'))
#                     # Application des conditions
#                     if total_weight == self.group_id.seuil:
#                         price = self.group_id.price1
#                     elif total_weight > self.group_id.seuil:
#                         price = self.group_id.price2
#                     else:
#
#                         continue
#                         # Si le poids est inférieur au seuil, on passe au suivant
#                     # Ajout de la ligne de paiement
#                     payment_lines.append((0, 0, {
#                         'farmer_id': farmer.id,
#                         'total_weight': total_weight,
#                         'price': price,
#                     }))
#                 self.payment_line_ids = payment_lines