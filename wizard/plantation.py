# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from odoo import fields, models, exceptions


class planting_payslip_plantation(models.TransientModel):
    _name = 'planting.payslip.plantation'
    _description = 'Generer les bulletin de paie par plantation'


    @property
    def _get_available_contracts_domain(self):
        run_pool = self.env['planting.payslip.run']
        obj = run_pool.browse(self.env.context.get('active_ids', []))
        sql = """ select distinct farmer_id from farmer_pay where state='un_paid' and date between %s and %s"""
        params = [obj.date_start, obj.date_end]
        self._cr.execute(sql, tuple(params))
        records = self._cr.fetchall()
        if not records:
            raise exceptions.ValidationError("Pas de paiement pour cette periode")
        list = []
        for line in records:
            list.append(line)
        return [('id', 'in', (tuple(list)))]

    def _get_partner(self):
        return self.env['res.partner'].search(self._get_available_contracts_domain)

    partner_ids = fields.Many2many('res.partner',string='Planteurs/Transporteurs',default=lambda self: self._get_partner())

    def compute_sheet(self):
        payslips = []
        run_data = None
        active_id = self.env.context.get('active_ids')
        if active_id:
            run_data = self.env['planting.payslip.run'].browse(active_id)
        if not self.partner_ids:
            raise exceptions.UserError("Vous devez Selectionner des lignes à payer.")
        if run_data.slip_ids:
            run_data.slip_ids.unlink()
        for partner in self.partner_ids:
            res = {
                'partner_id': partner.id or False,
                'struct_id': run_data.struct_id.id,
                'payslip_run_id': run_data.id,
                'date_from': run_data.date_start,
                'date_to': run_data.date_end,
            }
            payslip = self.env['planting.payslip'].create(res)
            payslip.onchange_partner()
            payslips.append(payslip.id)

        run_data.write({'state': 'verifed'})
        self.env['planting.payslip'].browse(payslips).compute_sheet()
        run_data.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}


class PlantingWzGlobal(models.TransientModel):
    _name = 'planting.wz.type'
    _description = 'Wizard Type Achat'

    date_start = fields.Date(string="Date Debut", required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    date_end = fields.Date(string="Date Fin", required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    type_id = fields.Many2one(comodel_name="type.farmer", string="Type plantation", required=False)
    bank_id = fields.Many2one(comodel_name="res.bank", string="Banque", required=False)
    type = fields.Selection(string='Type',selection=[('simple', 'Synthese'),('global', 'Synthese Generale'),('order', 'Etat Paie'), ],default="simple")


    def action_print_accounting(self):
        domain = [('date_due', '>=',self.date_start), ('date_due', '<=',self.date_end)]
        res = self.env['planting.account.move'].search(domain)
        account_ids = []

        res_filter = None
        if not res:
            raise exceptions.ValidationError("Pas d'analyse(s) pour cette cette periode")
        for rec in res :
            account_ids.append(rec.id)
            res_filter = [('id','in', tuple(account_ids))]
        return {"view_mode": 'tree', 'name': 'Journal de Control', "domain": res_filter,
                    'res_model': 'planting.account.move', 'type': 'ir.actions.act_window' }


    def action_print(self):
        for po in self:
            total_apromac = total_qty = total_net = 0
            self._cr.execute(""" Truncate table report_planting cascade """)
            domain = [('state', '=','done'),('date_from','>=',po.date_start),('date_to','<=',po.date_end)]
            if po.type_id:
                domain.append(('partner_id.type_id','=',po.type_id.id))

            res = self.env['planting.payslip'].search(domain)
            if res:
                report_id = self.env['report.planting'].create({
                    'date_start': po.date_start,
                    'date_end': po.date_end,
                    'type_id': po.type_id and po.type_id.id or False,
                    'type': po.type,
                })
                if po.type == "global":
                    type_ids = self.env['type.farmer'].search([])
                    res_price = self.env['planting.pricing'].search([('date','>=',po.date_start),('date','<=',po.date_end)],limit=1,order="date desc")
                    line_ids = res_price and res_price.price or 0
                    for type_id in type_ids:
                        total = sum([record.amount_pesee for record in res.filtered(lambda x: x.partner_id.type_id == type_id)])
                        total_qty += total
                        total_apromac += total * line_ids
                        self.env['report.planting.line'].create({
                            'ref': type_id.code,
                            'type_id': type_id.id,
                            'price': line_ids,
                            'qty': total,
                            'amount': total * line_ids,
                            'report_id': report_id.id,
                        })
                if po.type == "simple":
                    for payslip in res:
                        total_qty += payslip.amount_pesee
                        total_apromac += payslip.amount_pesee*payslip.price
                        total_net += payslip.amount_net
                        self.env['report.planting.line'].create({
                            'ref': payslip.number,
                                'number': payslip.partner_id.ref,
                                'partner_id': payslip.partner_id.id,
                                'type_id': payslip.partner_id.type_id.id,
                                'price': payslip.price,
                                'qty': payslip.amount_pesee,
                                'amount': payslip.amount_pesee*payslip.price,
                                'amount_net': payslip.amount_net,
                                'report_id': report_id.id,
                        })

                report_id.write({
                    "total": total_apromac,
                    "total_qty": total_qty,
                    "total_net": total_net,
                })
                return {"view_mode": 'tree,form', 'name':'Synthese des Achats',
                        'res_model': 'report.planting', 'type': 'ir.actions.act_window', }
            else:
                raise exceptions.ValidationError("Pas d'analyse(s) pour cette cette periode")

    def action_confirm(self):
        for po in self:
            total_net = 0
            self._cr.execute(""" Truncate table report_planting cascade """)

            domain = [('state', '=','close'),('date_start','>=',po.date_start),('date_end','<=',po.date_end)]

            res_run = self.env['planting.payslip.run'].search(domain)
            if res_run:
                report_id = self.env['report.planting'].create({
                    'date_start': po.date_start,
                    'date_end': po.date_end,
                    'bank_id': po.bank_id and po.bank_id.id or False,
                    'type': po.type,
                })
                res = res_run.slip_ids
                if po.bank_id:
                    res = res_run.slip_ids.filtered(lambda x: x.bank_id == po.bank_id)
                for payslip in res:
                    total_net += payslip.amount_net
                    self.env['report.order.line'].create({
                        'amount': payslip.amount_net,
                        'partner_id': payslip.partner_id.id,
                        'num': payslip.acc_number,
                        'bank_id': payslip.bank_id.id,
                        'report_id': report_id.id,
                        })

                report_id.write({ "total_net": total_net })
                return {"view_mode": 'tree,form', 'name':'Etat de paie',
                        'res_model': 'report.planting', 'type': 'ir.actions.act_window', }
            else:
                raise exceptions.ValidationError("Pas d'analyse(s) pour cette cette periode")


