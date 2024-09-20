# -*- coding: utf-8 -*-
import time
from odoo import models, fields, exceptions, api,_
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class PlantationMyp(models.Model):
    _name = 'plantation.myp'
    _description = 'Moyens de paiement'

    name = fields.Char('Libelle', required=True)

class FrequencyPayroll(models.Model):
    _name = 'frequency.payroll'
    _description = 'Moyens de paiement'

    name = fields.Char('Libelle', required=True)
    factor_day = fields.Integer(string='Facteyr en jrs', required=True)

class Village(models.Model):
    _name = 'farmer.village'
    _description = 'Village Plantation'

    name = fields.Char("Nom du village",required=True)
    sector_id = fields.Many2one(comodel_name="sector.sector", string="Département", required=False, )
    plantation_ids = fields.One2many('plantation.plantation', 'village_id', string='Plantations')




class TypeFarmer(models.Model):
    _name = "type.farmer"
    _description = "Type de plantation"

    name = fields.Char('Libelle',required=True)
    code = fields.Char('Code',required=True)
    seq_id = fields.Many2one(comodel_name="ir.sequence", string="Sequence", required=False,)

    @api.model_create_multi
    def create(self, values):
        res = super(TypeFarmer, self).create(values)
        seq = self.env['ir.sequence'].create({
            'name': res.name + " Plantation",
            'active': True,
            'prefix': res.code,
            'padding': 6
        })
        res.seq_id = seq.id
        return res

class Sector(models.Model):
    _name = 'sector.sector'
    _description = 'Région Plantation'

    name = fields.Char("Département",required=True)
    code = fields.Char("Code",required=True)
    locality_id = fields.Many2one(comodel_name="locality.locality", string="Région", required=False,)
    seq_id = fields.Many2one(comodel_name="ir.sequence", string="Sequence", required=False,)
    village_ids = fields.One2many(comodel_name="farmer.village", inverse_name="sector_id", string="Village", required=False, )

    @api.model_create_multi
    def create(self, values):
        res = super(Sector, self).create(values)
        seq = self.env['ir.sequence'].create({
            'name': res.name + " Code localité",
            'active': True,
            'prefix': res.code,
            'padding': 6
        })
        res.seq_id = seq.id
        return res

class Locality(models.Model):
    _name = "locality.locality"
    _description = " Région plantation"

    name = fields.Char('Région',required=True)
    # code = fields.Char('Code zone',required=True)
    sector_ids = fields.One2many(comodel_name="sector.sector", inverse_name="locality_id", string="Département", required=False,)

class GroupPrice(models.Model):
    _name = "group.group"
    _description = " Groupe de prix"

    name = fields.Char('Groupe',required=True)
    line_farmer_ids = fields.One2many(comodel_name="res.partner", inverse_name="group_id", string="Planteurs", required=False,)
    line_ids = fields.One2many(comodel_name="planting.pricing.line", inverse_name="group_id", string="Prix Planteurs", required=False,)




class PlantingPricing(models.Model):
    _name = "planting.pricing"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Historique Prix Planteurs"
    _order = "date desc"

    @api.model
    def default_get(self, values):
        res = super(PlantingPricing, self).default_get(values)
        if 'date' in values:
            res['name'] = "Prix Planteur " + time.strftime('%d/%m/%Y')
        return res

    name = fields.Char(string='Periode de prix', required=True)
    date = fields.Date(string='Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    line_ids = fields.One2many(comodel_name='planting.pricing.line',inverse_name='price_id', tracking=True, string='Ligne de prix',required=False)

    @api.onchange('date')
    def onchange_date(self):
        if self.date:
            self.name = "Prix Planteur " + self.date.strftime('%d/%m/%Y')

class PlantingPricingLine(models.Model):
    _name = "planting.pricing.line"
    _description = "Ligne Prix Planteurs"
    _order = "date desc"

    price_id = fields.Many2one(comodel_name='planting.pricing',string='Historique prix ',required=True, ondelete="cascade")
    group_id = fields.Many2one(comodel_name='group.group',string='Groupe planteur',required=True)
    prix_apromac= fields.Float(string='prix apromac ', digits="Product Unit Of Measure", required=True,)
    price = fields.Float(string='Prix ', digits="Product Unit Of Measure", required=True,)
   # < !--  ################ price1 10/09/24  ##############-->
  #  price1 = fields.Float(string='Prix NON EUDR', digits="Product Unit Of Measure", required=True,)
    price_driver = fields.Float(string='Transport (T)', digits="Product Unit Of Measure", required=True,)
    prime = fields.Float(string='Prime EUDR', digits="Product Unit Of Measure", required=True,)
    prime1 = fields.Float(string='Prime NON EUDR', digits="Product Unit Of Measure", required=True,)
    date = fields.Date(string='Date', related="price_id.date", store=True)


class ConfigurationPlanting(models.Model):
    _name = 'config.payslip.planting'
    _description = 'Configuration plantation'

    name = fields.Char("Libelle")
    tax_bic = fields.Float(string='Impot BIC',digits=(6,3), required=False)
    # driver = fields.Monetary(string='Prix transporteur', required=False)
    airsi = fields.Float(string='AIRSI',digits=(6,3), required=False)
    aiph = fields.Float(string='AIPH',digits=(6,3), required=False)
    chph = fields.Float(string='CHPH',digits=(6,3), required=False)
    number = fields.Integer(string='Sequence journal de Controle')
    default_frequency_id = fields.Many2one('frequency.payroll',string="Frequence de paie")
    company_id = fields.Many2one('res.company',string="Societé",default=lambda self: self.company_id)
    currency_id = fields.Many2one('res.currency',string="Devise",default=lambda self: self.env.company.currency_id)



class planting_salary_rule_category(models.Model):
    """
    HR Salary Rule Category
    """

    _name = 'planting.salary.rule.category'
    _description = 'Categorie de rubrique'

    name = fields.Char('Libelle', required=True, readonly=False)
    code = fields.Char('Code', size=64, required=True, readonly=False)
    note = fields.Text('Description')
    farmer = fields.Boolean('Planteur')
    company_id = fields.Many2one('res.company', 'Company', required=False, default=lambda self: self.env.user.company_id.id)


class Planting_rule_input(models.Model):

    _name = 'planting.rule.input'
    _description = 'Entrees'

    name = fields.Char('Description', required=True)
    code = fields.Char('Code', size=52, required=True, help="The code that can be used in the salary rules")
    rule_id = fields.Many2one('planting.salary.rule', 'Régle salariales', required=True)
    farmer = fields.Boolean('Planteur')


class payroll_structure(models.Model):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions

    """


    _name = 'planting.payroll.structure'
    _description = 'Structure de paie'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Libelle', required=True)
    company_id = fields.Many2one('res.company', 'Societe', required=True, copy=False,
                                 default=lambda self: self.env.user.company_id.id)
    note = fields.Text('Description')

    rule_ids = fields.Many2many('planting.salary.rule', 'planting_structure_salary_rule_rel', 'struct_id', 'rule_id',
                                'Rubriques')
    farmer = fields.Boolean('Planteur', default=False)



    def get_all_rules(self, structure_ids):
        """
        @param structure_ids: list of structure
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """

        all_rules = []
        for struct in self.env['planting.payroll.structure'].browse(structure_ids):
            all_rules += self.env['planting.salary.rule']._recursive_search_of_rules(struct.rule_ids)

        return all_rules


class planting_salary_rule(models.Model):

    _name = 'planting.salary.rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Libelle', required=True, readonly=False)
    code = fields.Char('Code', size=64, required=True, help="The code of salary rules can be used as reference in computation of other rules. In that case, it is case sensitive.")
   # code1 = fields.Char('Code1', size=64, required=True, help="The code of salary rules can be used as reference in computation of other rules. In that case, it is case sensitive.")
    sequence = fields.Integer('Sequence',default=5, required=True, help='Use to arrange calculation sequence', select=True)
    quantity = fields.Char('Quantity', default=1,help="It is used in computation for percentage and fixed amount.For e.g. A rule for Meal Voucher having fixed amount of 1€ per worked day can have its quantity defined in expression like worked_days.WORK100.number_of_days.")
   # quantity1 = fields.Char('Quantity NON EUDR', default=1,help="It is used in computation for percentage and fixed amount.For e.g. A rule for Meal Voucher having fixed amount of 1€ per worked day can have its quantity defined in expression like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('planting.salary.rule.category', 'Categorie', required=True)
    # paiement_id = fields.Many2one('paiement.paiement', 'Paiement prime Exceptionnelle', required=True)
    active = fields.Boolean('Active',default=True, help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip =  fields.Boolean('Apparaitre sur le bulletin',default=True, help="Used to display the salary rule on payslip.")
    company_id = fields.Many2one('res.company', 'Societé', required=False, default=lambda self: self.env.user.company_id.id)
    condition_select =  fields.Selection([('none', 'Toujours vrai'),('range', 'Pourcentage'), ('python', 'Expression Python ')], "Condition Basée sur", required=True,default="none")
    condition_range = fields.Char('Pourcentage Basé sur', readonly=False, help='This will be used to compute the % fields values; in general it is on basic, but you can also use categories code fields in lowercase as a variable names (hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text('Condition Python ', required=False, readonly=False, default='''
    # Available variables:
    #----------------------
    # payslip: object containing the payslips
    # partner: partner object
    # rules: object containing the rules code (previously computed)
    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
    # config: object containing the computed config planting
    # inputs: object containing the computed inputs.

    # Note: returned value have to be set in the variable 'result'

    result = rules.NET > categories.NET * 0.10''',help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float('% Minimum ', required=False, help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float('% Maximum ', required=False, help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
            ('percentage','Pourcentage (%)'),
            ('fix','Montant fixe '),
            ('code','Code Python'),
        ],'Type de Montant ', select=True, required=True, default="fix",help="The computation method for the rule amount.")
    amount_fix = fields.Float('Montant Fixe', digits=(6,2))
    amount_percentage = fields.Float('Percentage (%)', digits=(6,2), help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text('Code Python ')
    amount_percentage_base = fields.Char('Percentage basé sur ', required=False, readonly=False, help='result will be affected to a variable')
    input_ids = fields.One2many('planting.rule.input', 'rule_id', 'Entrée', copy=True)
    note = fields.Text('Description')
    farmer = fields.Boolean('Planteur')
    # account_debit = fields.Char('Compte Debit')
    # account_credit = fields.Char('Compte credit')
    debit_account_id = fields.Many2one('account.account', 'Compte de debit', help="Compte de debit")
    # credit_account_id =  fields.Many2one('account.account', 'Compte de credit', help="Compte de credit")





    def compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the current computation environment
        :return: returns a tuple (amount, qty, rate)
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix or 0.0, float(safe_eval(self.quantity, localdict)), 100.0
            except Exception as e:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).\nErreur: %s') % (self.name, self.code, e))
        if self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                     #   float(safe_eval(self.quantity1, localdict)),
                        self.amount_percentage or 0.0)
            except Exception as e:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).\nError: %s') % (self.name, self.code, e))
        else:  # python code
            try:
                safe_eval(self.amount_python_compute or 0.0, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), localdict.get('result_qty', 1.0), localdict.get('result_rate', 100.0)
            except Exception as e:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).\nError: %s') % (self.name, self.code, e))

    def satisfy_condition(self, localdict):
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        if self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except:
                raise UserError('Condition de plage incorrecte définie pour la règle de salaire %s (%s).') % (self.name, self.code)
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except:
                raise UserError('Mauvais code python pour a règle salariale %s (%s).') % (self.name, self.code)



class PlantingAccounting(models.Model):
    _name = 'planting.account.move'
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


class PlantingJournalControl(models.Model):
        _name = 'planting.journal.control'
        _description = 'Journal de Contrôle'

        name = fields.Char(string="Nom")
        date_start = fields.Date(string="Date de Début")
        date_end = fields.Date(string="Date de Fin")
        company_id = fields.Many2one('res.company', string="Société")


