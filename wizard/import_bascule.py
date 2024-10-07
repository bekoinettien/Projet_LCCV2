from odoo import fields, models,api,exceptions
import base64
import os
import time
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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
    property_account_payable_id = fields.Many2one('account.account', string="Compte Fournisseur")


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
    _description = 'Paiement des primes'


    group_id = fields.Many2one('prime.prime', string="Groupe")
    name = fields.Char(string="Référence", required=False, default=lambda self: self.env['ir.sequence'].next_by_code('paiement.reference'))
    date_from = fields.Date(string="Date de début")
    date_to = fields.Date(string="Date de fin")
    payment_line_ids = fields.One2many(comodel_name='payment.line', inverse_name='payment_id', string="Lignes de Paiement")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('paid', 'Payé'),
        ('cancelled', 'Fermer')
    ], string='État', default='draft')


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


    # @api.onchange('selection_id')
    #     def _onchange_selection_id(self):
    #         """Synchronise les informations de la sélection choisie."""
    #         if self.selection_id:
    #             self.group_id = self.selection_id.prime_id
    #             self.date_from = self.selection_id.datedebut
    #             self.date_to = self.selection_id.datefin
    #
    #             # Vider les lignes de paiement
    #             self.payment_line_ids = [(5, 0, 0)]  # 5 = 'unlink', vide les lignes existantes
    #
    #             # Calculer les lignes de paiement après mise à jour
    #             self._compute_payment_lines()

    # def create_account_move(self, debit_account_id, debit, credit, line_type, name=False, number=0,
    #                         analytic_account_id=False):
    #     for record in self:
    #         self.env['prime.account.move'].create({
    #             'journal_code': "ACH_MP",
    #             'payslip_date': record.create_date,
    #             'invoice': record.payment_line_ids.farmer_id.code_farmer + "/" + record.date_from.strftime(
    #                 '%d%m%Y') + "-" + record.date_to.strftime('%d%m%Y'),
    #             'ref': str(number),
    #             'account_code': line_type == "C" and record.payment_line_ids.farmer_id.property_account_payable_id.code or debit_account_id.code,
    #             'partner_account': line_type == "C" and record.payment_line_ids.farmer_id.code_farmer or False,
    #             'name': line_type == "C" and "ACHAT FONDS DE TASSE " + record.payment_line_ids.farmer_id.name + " " + record.date_from.strftime(
    #                 '%d %m') + " au " + record.date_to.strftime('%d %m %Y') or name,
    #             'date_due': record.date_from,
    #             'debit': debit,
    #             'credit': credit,
    #             'analytic': analytic_account_id,  # Ajout du compte analytique ici
    #             'type': line_type == "C" and "G" or line_type,
    #         })



    @api.onchange('group_id', 'date_from', 'date_to')
    def _compute_payment_lines(self):
        """Calcul des lignes de paiement basé sur le groupe et la période."""
        if self.group_id and self.date_from and self.date_to:
            selections = self.env['selection.selection'].search([
                ('prime_id', '=', self.group_id.id),
                ('datedebut', '<=', self.date_to),
                ('datefin', '>=', self.date_from),
                ('active', '=', True)
            ])

            if not selections:
                raise exceptions.UserError("Aucune prime active trouvée pour le groupe à cette période.")

            payment_lines = []
            seen_farmers = set()  # Pour garder une trace des planteurs déjà traités
            for farmer in self.group_id.farmer_ids:
                if farmer.id in seen_farmers:
                    continue  # Ignorer si le planteur a déjà été traité

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
                    bank_account = self.env['res.partner.bank'].search([('partner_id', '=', farmer.id)], limit=1)

                    payment_lines.append((0, 0, {
                        'farmer_id': farmer.id,
                        'total_weight': total_weight,
                        'price': prime,
                        'amount': prime,
                        'bank_id': bank_account.bank_id.id if bank_account else False,
                        'acc_number': bank_account.acc_number if bank_account else False,
                    }))

                    # Ajouter le planteur à l'ensemble pour éviter les doublons
                    seen_farmers.add(farmer.id)

            self.payment_line_ids = payment_lines


    def action_pay(self):
       # self.write({'state': 'paid'})
        # Copier les lignes de paiement validées dans une autre vue liste
        validated_payment_model = self.env['validated.payment']

        for line in self.payment_line_ids:
            validated_payment_model.create({
                'payment_id': self.id,
                'farmer_id': line.farmer_id.id,
                'total_weight': line.total_weight,
                'price': line.price,
                'amount': line.amount,
                'bank_id': line.bank_id.id if line.bank_id else False,
                'myp_id': line.myp_id,
                'acc_number': line.acc_number
            })
        for record in self:
            record.action_account_move()
        return self.write({'state': 'paid'})
       # self.create_account_move()
            ########################################################################################
    def create_account_move(self, debit_account_code, debit, credit, line_type, name=False, number=0, farmer_code=None):
        """Créer une écriture comptable pour un planteur donné"""
        move = self.env['prime.account.move'].create({
            'journal_code': "ACH_MP",
            'payslip_date': self.create_date,
            'invoice': farmer_code or 'N/A',
            'ref': str(number),
            'account_code': line_type == "C" and self.env['res.partner'].search(
                [('code_farmer', '=', farmer_code)]).property_account_payable_id.code or debit_account_code,
            'partner_account': farmer_code,
            'name': line_type == "C" and "PRIME EXCEPTIONNELLE " + name + " " + self.date_from.strftime(
                '%d %m') + " au " + self.date_to.strftime('%d %m %Y') or name,
            'date_due': self.date_from,
            'debit': debit,
            'credit': credit,
            'analytic': line_type == "A" and "L0101000" or False,
            'type': line_type == "C" and "G" or line_type,
        })
        _logger.info(f"Écriture comptable créée pour {name} : Débit {debit}, Crédit {credit}, Type {line_type}")

    def action_account_move(self):
        """Créer des écritures comptables par planteur avec trois lignes : Débit, Analytique, Crédit"""
        config = self.env['config.payslip.planting'].search([], limit=1)

        for record in self:
            # Dictionnaire pour stocker les montants par planteur
            for line in record.payment_line_ids:
                farmer = line.farmer_id
                farmer_code = line.farmer_id.code_farmer

                # 1. Créer l'écriture de Débit pour le planteur
                record.create_account_move(debit_account_code='6032111', debit=line.amount, credit=0, line_type="G",
                                           name=farmer.name, number=config.number, farmer_code=farmer_code)

                # 2. Créer l'écriture de Débit Analytique
                record.create_account_move(debit_account_code='6032111', debit=line.amount, credit=0, line_type="A",
                                           name=farmer.name, number=config.number, farmer_code=farmer_code)

                # 3. Créer l'écriture de Crédit pour le produit 'fonds de tasse'
                record.create_account_move(debit_account_code='6032111', debit=0, credit=line.amount, line_type="C",
                                           name="PRIME EXCEPTIONNELLE " + farmer.name, number=config.number + 1,
                                           farmer_code=farmer_code)
                config.number = config.number + 2

                _logger.info(
                    f"Planteur: {farmer.name}, Débit: {line.amount}, Crédit: {line.amount}, Code Planteur: {farmer_code}")

            # Incrémentation du numéro de configuration
            config.number += 1

    # def close_paiement(self):
    #     """Ferme le paiement et effectue les écritures comptables"""
    #     for record in self:
    #         record.action_account_move()
    #     return self.write({'state': 'paid'})

        ###########################################################################################################
    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})




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
    def _onchange_farmer_id(self):
        """Récupérer automatiquement la banque et le numéro de compte associés au planteur."""
        if self.farmer_id:
            # Trouver les informations bancaires du planteur sélectionné
            bank_account = self.env['res.partner.bank'].search([
                ('partner_id', '=', self.farmer_id.id)
            ], limit=1)  # Récupérer le premier compte bancaire associé

            # Renseigner la banque et le numéro de compte si trouvé
            if bank_account:
                self.bank_id = bank_account.bank_id.id
                self.acc_number = bank_account.acc_number
            else:
                self.bank_id = False
                self.acc_number = ''

    @api.model
    def create(self, vals):
        """Empêcher la perte des informations bancaires lors de la création."""
        # Récupérer les informations bancaires lors de la création de la ligne si elles ne sont pas définies
        if vals.get('farmer_id') and not vals.get('bank_id') and not vals.get('acc_number'):
            bank_account = self.env['res.partner.bank'].search([
                ('partner_id', '=', vals['farmer_id'])
            ], limit=1)

            if bank_account:
                vals['bank_id'] = bank_account.bank_id.id
                vals['acc_number'] = bank_account.acc_number

        return super(PaymentLine, self).create(vals)

    def write(self, vals):
        """S'assurer que les informations bancaires ne disparaissent pas lors de la modification."""
        if vals.get('farmer_id') and not vals.get('bank_id') and not vals.get('acc_number'):
            bank_account = self.env['res.partner.bank'].search([
                ('partner_id', '=', vals['farmer_id'])
            ], limit=1)

            if bank_account:
                vals['bank_id'] = bank_account.bank_id.id
                vals['acc_number'] = bank_account.acc_number

        return super(PaymentLine, self).write(vals)
    ##################################################################


    ##################################################################


class ValidatedPayment(models.Model):
    _name = 'validated.payment'
    _description = 'Paiements Validés'

    name = fields.Char(string="Nom", required=True, default=lambda self: _('Nouveau'))
    payment_id = fields.Many2one('paiement.paiement', string="Paiement", required=True)
    date_range = fields.Char(string="Plage de Dates", compute="_compute_date_range", store=False)
    farmer_id = fields.Many2one('res.partner', string="Planteur", domain="[('farmer','=',True)]", required=True)
    code_farmer= fields.Char(string="Matricule Planteur", related='farmer_id.code_farmer', required=True)
    total_weight = fields.Float(string="Poids Total", required=True)
    price = fields.Float(string="Prix", required=True)
    amount = fields.Float(string="Montant", required=True)
    bank_id = fields.Many2one('res.bank', 'Banque', readonly=True)
    myp_id = fields.Many2one('plantation.myp', string="Mode de paiement", related="farmer_id.myp_id", readonly=True)
    acc_number = fields.Char('Numero compte', readonly=True)

    @api.depends('payment_id.date_from', 'payment_id.date_to')
    def _compute_date_range(self):
        for record in self:
            if record.payment_id:
                start_date = record.payment_id.date_from
                end_date = record.payment_id.date_to
                record.date_range = f"{start_date} - {end_date}" if start_date and end_date else "N/A"
            else:
                record.date_range = "N/A"



class PrimeAccounting(models.Model):
    _name = 'prime.account.move'
    _description = 'Journal de Control'

    journal_code = fields.Char("Code Journal")
    date_due = fields.Date("Date d'écheance ")
    payslip_date = fields.Date("Date pièce ")
    invoice = fields.Char("N° Facture")
    ref = fields.Char("Reference")
    account_code = fields.Char("Compte Général")
    #account_id = fields.Many2one('account.account',"Compte Général")
    partner_account = fields.Char("Compte Tierce ")
    name = fields.Char("Libelle")
    type = fields.Char("Type ecriture")
    analytic = fields.Char("Section Analytique")
    number_move = fields.Char("N° Piece")
    debit = fields.Float(string='Debit', required=False)
    credit = fields.Float(string='Credit', required=False)
    #ajouter 06/09/24




