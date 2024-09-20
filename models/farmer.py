# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
##############################################################################

from odoo import fields, models, api


class Product(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    code = fields.Char('Code')

class Farmers(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Planteurs'

    plantation_ids = fields.One2many('plantation.plantation', 'partner_id', 'Plantations')
    farmer = fields.Boolean('Planteur')
    myp_id = fields.Many2one('plantation.myp', string="Mode Reglement", )
    struct_id = fields.Many2one('planting.payroll.structure', string="Structure Salariale",)
    type_id = fields.Many2one('type.farmer', string="Type Planteur",)
    group_id = fields.Many2one('group.group', required=True, string="Groupe Tarification Planteur",)
    birthday = fields.Date(string='Date Immatriculation', required=False)
    number_aprocmac = fields.Char(string='Numero identification aprocmac', required=False)
    code_farmer = fields.Char(string='Code Planteur', required=True, index=True)
    prime_id = fields.Many2one('prime.prime', string="Groupe",required=False)

    @api.model
    def create(self, values):
        if values.get('farmer') :
            type_farmer = self.env['type.farmer'].browse(values['type_id'])
            values['ref'] = type_farmer.seq_id.next_by_id()
        return super(Farmers, self).create(values)

# Plantations

class Plantation(models.Model):
    _name = 'plantation.plantation'
    _description = 'Plantations'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Identification plantation',required=True)
    number_geo = fields.Char('Numero Géolocalise')
    partner_id = fields.Many2one("res.partner", string="Planteur", required=False,ondelete="cascade", domain=[('farmer', '=', True)])
    frequency_id = fields.Many2one('frequency.payroll', string="Frequence de paie", required=True)
    area = fields.Char(string='Superficie',required=False)
    locality_id = fields.Many2one("locality.locality","Région",required=False)
    sector_id = fields.Many2one("sector.sector","Département",required=False)
    village_id = fields.Many2one("farmer.village","Village",required=False)
    date = fields.Char("Date Immatriculation",required=False)
    code_farmer = fields.Char(string='Code Planteur', required=False)

#permettant de recuperer le code_farmer du planteur pour l'affecter a son partner.id
    @api.model
    def create(self, vals):
        if vals.get('code_farmer'):
            partner = self.env['res.partner'].search([('code_farmer', '=', vals['code_farmer'])], limit=1)
            if partner:
                vals['partner_id'] = partner.id
            else:
                raise ValueError(f"Planteur avec code_farmer '{vals['code_farmer']}' non trouvé")
            del vals['code_farmer']
        return super(Plantation, self).create(vals)







