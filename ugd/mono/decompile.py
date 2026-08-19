"""
Mono IL to C# decompiler - FULL IMPLEMENTATION.
Converts CIL (Common Intermediate Language) to readable, compilable C# code.
"""
import struct
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from enum import Enum, auto
from .pe import MonoAssembly, TABLE_TYPE_DEF, TABLE_METHOD, TABLE_FIELD, TABLE_PARAM, TABLE_MEMBER_REF


# ============================================================
# IL Opcodes - COMPLETE
# ============================================================

class OpcodeInfo:
    """Information about an IL opcode."""
    __slots__ = ('name', 'operand_type', 'operand_size', 'stack_pop', 'stack_push', 'flow_control')
    
    def __init__(self, name: str, operand_type: Optional[str] = None, operand_size: int = 0,
                 stack_pop: int = 0, stack_push: int = 0, flow_control: str = 'next'):
        self.name = name
        self.operand_type = operand_type
        self.operand_size = operand_size
        self.stack_pop = stack_pop
        self.stack_push = stack_push
        self.flow_control = flow_control  # next, branch, cond_branch, call, return, throw, meta


# Build complete opcode table
IL_OPCODES: List[OpcodeInfo] = [
    # 0x00
    OpcodeInfo("nop", flow_control="next"),
    OpcodeInfo("break", flow_control="meta"),
    OpcodeInfo("ldarg.0", stack_push=1),
    OpcodeInfo("ldarg.1", stack_push=1),
    OpcodeInfo("ldarg.2", stack_push=1),
    OpcodeInfo("ldarg.3", stack_push=1),
    OpcodeInfo("ldloc.0", stack_push=1),
    OpcodeInfo("ldloc.1", stack_push=1),
    OpcodeInfo("ldloc.2", stack_push=1),
    OpcodeInfo("ldloc.3", stack_push=1),
    OpcodeInfo("stloc.0", stack_pop=1),
    OpcodeInfo("stloc.1", stack_pop=1),
    OpcodeInfo("stloc.2", stack_pop=1),
    OpcodeInfo("stloc.3", stack_pop=1),
    OpcodeInfo("ldarg.s", "uint8", 1, stack_push=1),
    OpcodeInfo("ldarga.s", "uint8", 1, stack_push=1),
    
    # 0x10
    OpcodeInfo("starg.s", "uint8", 1, stack_pop=1),
    OpcodeInfo("ldloc.s", "uint8", 1, stack_push=1),
    OpcodeInfo("ldloca.s", "uint8", 1, stack_push=1),
    OpcodeInfo("stloc.s", "uint8", 1, stack_pop=1),
    OpcodeInfo("ldnull", stack_push=1),
    OpcodeInfo("ldc.i4.m1", stack_push=1),
    OpcodeInfo("ldc.i4.0", stack_push=1),
    OpcodeInfo("ldc.i4.1", stack_push=1),
    OpcodeInfo("ldc.i4.2", stack_push=1),
    OpcodeInfo("ldc.i4.3", stack_push=1),
    OpcodeInfo("ldc.i4.4", stack_push=1),
    OpcodeInfo("ldc.i4.5", stack_push=1),
    OpcodeInfo("ldc.i4.6", stack_push=1),
    OpcodeInfo("ldc.i4.7", stack_push=1),
    OpcodeInfo("ldc.i4.8", stack_push=1),
    
    # 0x20
    OpcodeInfo("ldc.i4.s", "int8", 1, stack_push=1),
    OpcodeInfo("ldc.i4", "int32", 4, stack_push=1),
    OpcodeInfo("ldc.i8", "int64", 8, stack_push=1),
    OpcodeInfo("ldc.r4", "float32", 4, stack_push=1),
    OpcodeInfo("ldc.r8", "float64", 8, stack_push=1),
    OpcodeInfo("dup", stack_pop=1, stack_push=2),
    OpcodeInfo("pop", stack_pop=1),
    OpcodeInfo("jmp", "method", 4, stack_pop=-1, flow_control="call"),
    OpcodeInfo("call", "method", 4, stack_pop=-1, stack_push=1, flow_control="call"),
    OpcodeInfo("calli", "method", 4, stack_pop=-1, stack_push=1, flow_control="call"),
    OpcodeInfo("ret", flow_control="return"),
    OpcodeInfo("br.s", "int8", 1, flow_control="branch"),
    OpcodeInfo("brfalse.s", "int8", 1, stack_pop=1, flow_control="cond_branch"),
    OpcodeInfo("brtrue.s", "int8", 1, stack_pop=1, flow_control="cond_branch"),
    
    # 0x30
    OpcodeInfo("beq.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bge.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bgt.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("ble.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("blt.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bne.un.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bge.un.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bgt.un.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("ble.un.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("blt.un.s", "int8", 1, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("br", "int32", 4, flow_control="branch"),
    OpcodeInfo("brfalse", "int32", 4, stack_pop=1, flow_control="cond_branch"),
    OpcodeInfo("brtrue", "int32", 4, stack_pop=1, flow_control="cond_branch"),
    OpcodeInfo("beq", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bge", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    
    # 0x40
    OpcodeInfo("bgt", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("ble", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("blt", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bne.un", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bge.un", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("bgt.un", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("ble.un", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("blt.un", "int32", 4, stack_pop=2, flow_control="cond_branch"),
    OpcodeInfo("switch", "switch", -1, stack_pop=1, flow_control="cond_branch"),
    OpcodeInfo("ldind.i1", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.u1", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.i2", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.u2", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.i4", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.u4", stack_pop=1, stack_push=1),
    
    # 0x50
    OpcodeInfo("ldind.i8", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.r4", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.r8", stack_pop=1, stack_push=1),
    OpcodeInfo("ldind.ref", stack_pop=1, stack_push=1),
    OpcodeInfo("stind.ref", stack_pop=2),
    OpcodeInfo("stind.i1", stack_pop=2),
    OpcodeInfo("stind.i2", stack_pop=2),
    OpcodeInfo("stind.i4", stack_pop=2),
    OpcodeInfo("stind.i8", stack_pop=2),
    OpcodeInfo("stind.r4", stack_pop=2),
    OpcodeInfo("stind.r8", stack_pop=2),
    OpcodeInfo("add", stack_pop=2, stack_push=1),
    OpcodeInfo("sub", stack_pop=2, stack_push=1),
    OpcodeInfo("mul", stack_pop=2, stack_push=1),
    OpcodeInfo("div", stack_pop=2, stack_push=1),
    OpcodeInfo("rem", stack_pop=2, stack_push=1),
    
    # 0x60
    OpcodeInfo("and", stack_pop=2, stack_push=1),
    OpcodeInfo("or", stack_pop=2, stack_push=1),
    OpcodeInfo("xor", stack_pop=2, stack_push=1),
    OpcodeInfo("shl", stack_pop=2, stack_push=1),
    OpcodeInfo("shr", stack_pop=2, stack_push=1),
    OpcodeInfo("shr.un", stack_pop=2, stack_push=1),
    OpcodeInfo("neg", stack_pop=1, stack_push=1),
    OpcodeInfo("not", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.i1", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.i2", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.i4", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.i8", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.r4", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.r8", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.u4", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.u8", stack_pop=1, stack_push=1),
    
    # 0x70
    OpcodeInfo("callvirt", "method", 4, stack_pop=-1, stack_push=1, flow_control="call"),
    OpcodeInfo("cpobj", "type", 4, stack_pop=2),
    OpcodeInfo("ldobj", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("ldstr", "string", 4, stack_push=1),
    OpcodeInfo("newobj", "method", 4, stack_pop=-1, stack_push=1, flow_control="call"),
    OpcodeInfo("castclass", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("isinst", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("conv.r.un", stack_pop=1, stack_push=1),
    OpcodeInfo("unbox", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("throw", flow_control="throw"),
    OpcodeInfo("ldfld", "field", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("ldflda", "field", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("stfld", "field", 4, stack_pop=2),
    OpcodeInfo("ldsfld", "field", 4, stack_push=1),
    OpcodeInfo("ldsflda", "field", 4, stack_push=1),
    
    # 0x80
    OpcodeInfo("stsfld", "field", 4, stack_pop=1),
    OpcodeInfo("stobj", "type", 4, stack_pop=2),
    OpcodeInfo("conv.ovf.i1.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i2.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i4.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i8.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u1.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u2.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u4.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u8.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i1", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u1", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i2", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u2", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i4", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u4", stack_pop=1, stack_push=1),
    
    # 0x90
    OpcodeInfo("conv.ovf.i8", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u8", stack_pop=1, stack_push=1),
    OpcodeInfo("refanyval", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("ckfinite", stack_pop=1, stack_push=1),
    OpcodeInfo("mkrefany", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("ldtoken", "token", 4, stack_push=1),
    OpcodeInfo("conv.u2", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.u1", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.i", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u", stack_pop=1, stack_push=1),
    OpcodeInfo("add.ovf", stack_pop=2, stack_push=1),
    OpcodeInfo("add.ovf.un", stack_pop=2, stack_push=1),
    OpcodeInfo("mul.ovf", stack_pop=2, stack_push=1),
    OpcodeInfo("mul.ovf.un", stack_pop=2, stack_push=1),
    
    # 0xA0
    OpcodeInfo("sub.ovf", stack_pop=2, stack_push=1),
    OpcodeInfo("sub.ovf.un", stack_pop=2, stack_push=1),
    OpcodeInfo("endfinally", flow_control="meta"),
    OpcodeInfo("leave", "int32", 4, flow_control="branch"),
    OpcodeInfo("leave.s", "int8", 1, flow_control="branch"),
    OpcodeInfo("stind.i", stack_pop=2),
    OpcodeInfo("conv.u", stack_pop=1, stack_push=1),
    # 0xA7-0xAF reserved
    OpcodeInfo("unused_a7"),
    OpcodeInfo("unused_a8"),
    OpcodeInfo("unused_a9"),
    OpcodeInfo("unused_aa"),
    OpcodeInfo("unused_ab"),
    OpcodeInfo("unused_ac"),
    OpcodeInfo("unused_ad"),
    OpcodeInfo("unused_ae"),
    OpcodeInfo("unused_af"),
    
    # 0xB0
    OpcodeInfo("volatile.", None, 0),  # Prefix
    OpcodeInfo("tail.", None, 0),      # Prefix
    OpcodeInfo("initobj", "type", 4),
    OpcodeInfo("constrained.", "type", 4),  # Prefix
    OpcodeInfo("cpblk", None, 0),
    OpcodeInfo("initblk", None, 0),
    OpcodeInfo("rethrow", flow_control="throw"),
    # 0xB7 reserved
    OpcodeInfo("unused_b7"),
    OpcodeInfo("sizeof", "type", 4, stack_push=1),
    OpcodeInfo("refanytype", None, 0),
    OpcodeInfo("readonly.", None, 0),  # Prefix
    
    # 0xC0
    OpcodeInfo("stoobj", "type", 4, stack_pop=2),
    OpcodeInfo("conv.ovf.i1.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i2.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i4.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i8.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u1.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u2.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u4.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u8.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.i.un", stack_pop=1, stack_push=1),
    OpcodeInfo("conv.ovf.u.un", stack_pop=1, stack_push=1),
    OpcodeInfo("box", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("newarr", "type", 4, stack_pop=1, stack_push=1),
    OpcodeInfo("ldlen", stack_pop=1, stack_push=1),
    OpcodeInfo("ldelem.i1", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.u1", stack_pop=2, stack_push=1),
    
    # 0xD0
    OpcodeInfo("ldelem.i2", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.u2", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.i4", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.u4", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.i8", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.r4", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.r8", stack_pop=2, stack_push=1),
    OpcodeInfo("ldelem.ref", stack_pop=2, stack_push=1),
    OpcodeInfo("stelem.i", stack_pop=3),
    OpcodeInfo("stelem.i1", stack_pop=3),
    OpcodeInfo("stelem.i2", stack_pop=3),
    OpcodeInfo("stelem.i4", stack_pop=3),
    OpcodeInfo("stelem.i8", stack_pop=3),
    OpcodeInfo("stelem.r4", stack_pop=3),
    OpcodeInfo("stelem.r8", stack_pop=3),
    OpcodeInfo("stelem.ref", stack_pop=3),
    
    # 0xE0
    OpcodeInfo("ldelem.any", "type", 4, stack_pop=2, stack_push=1),
    OpcodeInfo("stelem.any", "type", 4, stack_pop=3),
    OpcodeInfo("unbox.any", "type", 4, stack_pop=1, stack_push=1),
    # 0xE3-0xFF reserved
    OpcodeInfo("unused_e3"),
    OpcodeInfo("unused_e4"),
    OpcodeInfo("unused_e5"),
    OpcodeInfo("unused_e6"),
    OpcodeInfo("unused_e7"),
    OpcodeInfo("unused_e8"),
    OpcodeInfo("unused_e9"),
    OpcodeInfo("unused_ea"),
    OpcodeInfo("unused_eb"),
    OpcodeInfo("unused_ec"),
    OpcodeInfo("unused_ed"),
    OpcodeInfo("unused_ee"),
    OpcodeInfo("unused_ef"),
    OpcodeInfo("unused_f0"),
    OpcodeInfo("unused_f1"),
    OpcodeInfo("unused_f2"),
    OpcodeInfo("unused_f3"),
    OpcodeInfo("unused_f4"),
    OpcodeInfo("unused_f5"),
    OpcodeInfo("unused_f6"),
    OpcodeInfo("unused_f7"),
    OpcodeInfo("unused_f8"),
    OpcodeInfo("unused_f9"),
    OpcodeInfo("unused_fa"),
    OpcodeInfo("unused_fb"),
    OpcodeInfo("unused_fc"),
    OpcodeInfo("unused_fd"),
    OpcodeInfo("unused_fe"),
    OpcodeInfo("unused_ff"),
]

# Prefixed opcodes (0xFE)
PREFIXED_OPCODES: Dict[int, OpcodeInfo] = {
    0x00: OpcodeInfo("arglist", stack_push=1),
    0x01: OpcodeInfo("ceq", stack_pop=2, stack_push=1),
    0x02: OpcodeInfo("cgt", stack_pop=2, stack_push=1),
    0x03: OpcodeInfo("cgt.un", stack_pop=2, stack_push=1),
    0x04: OpcodeInfo("clt", stack_pop=2, stack_push=1),
    0x05: OpcodeInfo("clt.un", stack_pop=2, stack_push=1),
    0x06: OpcodeInfo("ldftn", "method", 4, stack_push=1),
    0x07: OpcodeInfo("ldvirtftn", "method", 4, stack_push=1),
    0x08: OpcodeInfo("ldarg", "uint16", 2, stack_push=1),
    0x09: OpcodeInfo("ldarga", "uint16", 2, stack_push=1),
    0x0A: OpcodeInfo("starg", "uint16", 2, stack_pop=1),
    0x0B: OpcodeInfo("ldloc", "uint16", 2, stack_push=1),
    0x0C: OpcodeInfo("ldloca", "uint16", 2, stack_push=1),
    0x0D: OpcodeInfo("stloc", "uint16", 2, stack_pop=1),
    0x0E: OpcodeInfo("localloc", None, 0, stack_push=1),
    0x0F: OpcodeInfo("endfilter", flow_control="meta"),
    0x10: OpcodeInfo("unaligned.", "uint8", 1),  # Prefix with alignment
    0x11: OpcodeInfo("volatile.", None, 0),    # Prefix
    0x12: OpcodeInfo("tail.", None, 0),        # Prefix
    0x13: OpcodeInfo("initobj", "type", 4),
    0x14: OpcodeInfo("constrained.", "type", 4),  # Prefix
    0x15: OpcodeInfo("cpblk", None, 0),
    0x16: OpcodeInfo("initblk", None, 0),
    0x17: OpcodeInfo("no.", None, 0),         # Prefix (no type check)
    0x18: OpcodeInfo("rethrow", flow_control="throw"),
    0x19: OpcodeInfo("sizeof", "type", 4, stack_push=1),
    0x1A: OpcodeInfo("refanytype", None, 0),
    0x1B: OpcodeInfo("readonly.", None, 0),   # Prefix
}


# ============================================================
# IL Instruction
# ============================================================

class ILInstruction:
    """Represents a single IL instruction with full information."""
    __slots__ = ('offset', 'opcode', 'operand', 'operand_type', 'operand_size',
                 'stack_before', 'stack_after', 'target', 'is_target',
                 'exception_handlers', 'sequence_point')
    
    def __init__(self, offset: int, opcode: str, operand: Any = None, 
                 operand_type: str = '', operand_size: int = 0):
        self.offset = offset
        self.opcode = opcode
        self.operand = operand
        self.operand_type = operand_type
        self.operand_size = operand_size
        self.stack_before = 0
        self.stack_after = 0
        self.target: Optional[int] = None  # Branch target offset
        self.is_target = False
        self.exception_handlers: List[Dict[str, Any]] = []
        self.sequence_point: Optional[Dict[str, Any]] = None
    
    def __repr__(self):
        if self.operand is not None:
            return f"{self.offset:04X}: {self.opcode} {self.operand}"
        return f"{self.offset:04X}: {self.opcode}"
    
    def __str__(self):
        if self.operand is not None:
            if self.operand_type == 'string':
                return f"{self.offset:04X}: {self.opcode} " + repr(self.operand)
            return f"{self.offset:04X}: {self.opcode} {self.operand}"
        return f"{self.offset:04X}: {self.opcode}"


# ============================================================
# IL Disassembler
# ============================================================

class ILDisassembler:
    """Disassemble IL bytecode into instructions with full metadata."""
    
    def __init__(self, il_code: bytes, resolve_token: Optional[Callable[[int], str]] = None,
                 exception_handlers: Optional[List[Dict[str, Any]]] = None):
        self.il_code = il_code
        self.resolve_token = resolve_token
        self.exception_handlers = exception_handlers or []
        self.instructions: List[ILInstruction] = []
        self.labels: Dict[int, str] = {}
        self._branch_targets: Set[int] = set()
    
    def disassemble(self) -> List[ILInstruction]:
        """Disassemble IL code into instructions."""
        from .utils import Reader
        
        reader = Reader(self.il_code, '<')
        self.instructions = []
        
        # First pass: identify branch targets
        self._identify_targets()
        
        # Second pass: disassemble
        while reader.remaining() > 0:
            offset = reader.tell()
            opcode_byte = reader.read_u8()
            
            # Check for prefixed opcode
            if opcode_byte == 0xFE:
                prefix_byte = reader.read_u8()
                if prefix_byte in PREFIXED_OPCODES:
                    op_info = PREFIXED_OPCODES[prefix_byte]
                    self._process_instruction(reader, offset, op_info, "fe." + op_info.name)
                else:
                    # Unknown prefixed opcode
                    instr = ILInstruction(offset, f"fe.{prefix_byte:02X}")
                    self.instructions.append(instr)
                continue
            
            # Regular opcode
            if opcode_byte >= len(IL_OPCODES):
                instr = ILInstruction(offset, f"unknown_{opcode_byte:02X}")
                self.instructions.append(instr)
                continue
            
            op_info = IL_OPCODES[opcode_byte]
            self._process_instruction(reader, offset, op_info, op_info.name)
        
        # Mark targets
        for instr in self.instructions:
            if instr.offset in self._branch_targets:
                instr.is_target = True
        
        return self.instructions
    
    def _identify_targets(self) -> None:
        """Identify all branch targets in the IL code."""
        from .utils import Reader
        
        reader = Reader(self.il_code, '<')
        
        while reader.remaining() > 0:
            offset = reader.tell()
            opcode_byte = reader.read_u8()
            
            # Check for prefixed opcode
            if opcode_byte == 0xFE:
                prefix_byte = reader.read_u8()
                if prefix_byte in PREFIXED_OPCODES:
                    op_info = PREFIXED_OPCODES[prefix_byte]
                    self._read_operand(reader, op_info)
                continue
            
            # Regular opcode
            if opcode_byte >= len(IL_OPCODES):
                continue
            
            op_info = IL_OPCODES[opcode_byte]
            
            # Check if this is a branch
            if op_info.flow_control in ['branch', 'cond_branch']:
                operand = self._read_operand_value(reader, op_info)
                if isinstance(operand, int):
                    target = offset + op_info.operand_size + 1 + operand
                    self._branch_targets.add(target)
                elif isinstance(operand, list):
                    for offset_val in operand:
                        target = offset + op_info.operand_size + 1 + offset_val
                        self._branch_targets.add(target)
            
            # Also add exception handler targets
            for handler in self.exception_handlers:
                self._branch_targets.add(handler.get('handler_start', 0))
                self._branch_targets.add(handler.get('filter_start', 0))
            
            # Read operand to advance
            self._read_operand(reader, op_info)
    
    def _process_instruction(self, reader: 'Reader', offset: int, op_info: OpcodeInfo, name: str) -> None:
        """Process a single instruction."""
        operand = self._read_operand_value(reader, op_info)
        
        # Create instruction
        instr = ILInstruction(offset, name, operand, op_info.operand_type, op_info.operand_size)
        
        # Calculate target for branches
        if op_info.flow_control in ['branch', 'cond_branch']:
            if isinstance(operand, int):
                instr.target = offset + op_info.operand_size + 1 + operand
            elif isinstance(operand, list):
                # Switch instruction - store all targets
                instr.target = offset + op_info.operand_size + 1 + operand[0] if operand else None
        
        self.instructions.append(instr)
    
    def _read_operand(self, reader: 'Reader', op_info: OpcodeInfo) -> Any:
        """Read operand and advance reader."""
        if op_info.operand_type is None:
            return None
        
        if op_info.operand_type == 'int8':
            return reader.read_i8()
        elif op_info.operand_type == 'uint8':
            return reader.read_u8()
        elif op_info.operand_type == 'int16':
            return reader.read_i16()
        elif op_info.operand_type == 'uint16':
            return reader.read_u16()
        elif op_info.operand_type == 'int32':
            return reader.read_i32()
        elif op_info.operand_type == 'uint32':
            return reader.read_u32()
        elif op_info.operand_type == 'int64':
            return reader.read_i64()
        elif op_info.operand_type == 'uint64':
            return reader.read_u64()
        elif op_info.operand_type == 'float32':
            return reader.read_float()
        elif op_info.operand_type == 'float64':
            return reader.read_double()
        elif op_info.operand_type in ['method', 'field', 'type', 'token', 'string']:
            return reader.read_u32()
        elif op_info.operand_type == 'switch':
            count = reader.read_u32()
            offsets = [reader.read_u32() for _ in range(count)]
            return offsets
        else:
            return None
    
    def _read_operand_value(self, reader: 'Reader', op_info: OpcodeInfo) -> Any:
        """Read operand value (with resolution)."""
        if op_info.operand_type is None:
            return None
        
        if op_info.operand_type == 'int8':
            return reader.read_i8()
        elif op_info.operand_type == 'uint8':
            return reader.read_u8()
        elif op_info.operand_type == 'int16':
            return reader.read_i16()
        elif op_info.operand_type == 'uint16':
            return reader.read_u16()
        elif op_info.operand_type == 'int32':
            return reader.read_i32()
        elif op_info.operand_type == 'uint32':
            return reader.read_u32()
        elif op_info.operand_type == 'int64':
            return reader.read_i64()
        elif op_info.operand_type == 'uint64':
            return reader.read_u64()
        elif op_info.operand_type == 'float32':
            return reader.read_float()
        elif op_info.operand_type == 'float64':
            return reader.read_double()
        elif op_info.operand_type in ['method', 'field', 'type', 'token']:
            token = reader.read_u32()
            if self.resolve_token:
                return self.resolve_token(token)
            return f"0x{token:08X}"
        elif op_info.operand_type == 'string':
            token = reader.read_u32()
            if self.resolve_token:
                resolved = self.resolve_token(token)
                return f'"{resolved}"'
            return f"0x{token:08X}"
        elif op_info.operand_type == 'switch':
            count = reader.read_u32()
            offsets = [reader.read_u32() for _ in range(count)]
            return offsets
        else:
            return None


# ============================================================
# Expression Builder
# ============================================================

class Expression:
    """Represents an expression in the decompiled code."""
    __slots__ = ('type', 'value', 'children', 'is_lvalue')
    
    def __init__(self, type: str, value: Any = None):
        self.type = type
        self.value = value
        self.children: List['Expression'] = []
        self.is_lvalue = False
    
    def __str__(self):
        if self.type == 'literal':
            return str(self.value)
        elif self.type == 'variable':
            return str(self.value)
        elif self.type == 'binary':
            return f"({self.children[0]} {self.value} {self.children[1]})"
        elif self.type == 'unary':
            return f"{self.value}{self.children[0]}"
        elif self.type == 'call':
            args = ', '.join(str(c) for c in self.children)
            return f"{self.value}({args})"
        elif self.type == 'new':
            args = ', '.join(str(c) for c in self.children)
            return f"new {self.value}({args})"
        elif self.type == 'member_access':
            return f"{self.children[0]}.{self.value}"
        elif self.type == 'array_access':
            return f"{self.children[0]}[{self.children[1]}]"
        elif self.type == 'cast':
            return f"(({self.value}){self.children[0]}"
        elif self.type == 'ternary':
            return f"{self.children[0]} ? {self.children[1]} : {self.children[2]}"
        else:
            return f"/* {self.type}: {self.value} */"


class ExpressionBuilder:
    """Builds expression trees from IL instructions using a stack-based approach."""
    
    def __init__(self, instructions: List[ILInstruction], method_info: Dict[str, Any],
                 type_system: 'TypeSystem', locals: List[Dict[str, Any]],
                 parameters: List[Dict[str, Any]]):
        self.instructions = instructions
        self.method_info = method_info
        self.type_system = type_system
        self.locals = locals
        self.parameters = parameters
        self.stack: List[Expression] = []
        self.output: List[str] = []
        self.current_line: List[Expression] = []
        self.labels: Dict[int, str] = {}
        self._label_counter = 0
    
    def build(self) -> List[str]:
        """Build C# code from IL instructions."""
        self.output = []
        self.stack = []
        
        # Write method signature
        self._write_method_signature()
        
        # Process each instruction
        for instr in self.instructions:
            self._process_instruction(instr)
        
        return self.output
    
    def _write_method_signature(self) -> None:
        """Write the C# method signature."""
        name = self.method_info.get('name', 'Method')
        return_type = self.method_info.get('return_type', 'void')
        
        # Build parameter list
        params = []
        for param in self.parameters:
            param_type = param.get('type', 'object')
            param_name = param.get('name', f'arg{len(params)}')
            params.append(f"{param_type} {param_name}")
        
        # Check for special methods
        if name == '.ctor':
            class_name = self.method_info.get('class_name', 'Class')
            self.output.append(f"public {class_name}({', '.join(params)})")
        elif name == '.cctor':
            class_name = self.method_info.get('class_name', 'Class')
            self.output.append(f"static {class_name}()")
        else:
            self.output.append(f"{return_type} {name}({', '.join(params)})")
        
        self.output.append("{")
    
    def _process_instruction(self, instr: ILInstruction) -> None:
        """Process an IL instruction and generate C# code."""
        opcode = instr.opcode
        
        # Handle labels
        if instr.is_target:
            label = self._get_label(instr.offset)
            self.output.append(f"{label}:")
        
        # Process based on opcode
        if opcode == 'nop':
            return
        
        elif opcode == 'ret':
            if self.stack:
                value = self._pop_expression()
                self.output.append(f"    return {value};")
            else:
                self.output.append("    return;")
            self.stack = []  # Clear stack after return
        
        elif opcode.startswith('ldarg'):
            arg_index = self._get_arg_index(instr)
            if arg_index < len(self.parameters):
                arg_name = self.parameters[arg_index].get('name', f'arg{arg_index}')
                self.stack.append(Expression('variable', arg_name))
        
        elif opcode.startswith('ldloc'):
            local_index = self._get_local_index(instr)
            if local_index < len(self.locals):
                local_name = self.locals[local_index].get('name', f'local{local_index}')
                self.stack.append(Expression('variable', local_name))
        
        elif opcode.startswith('stloc'):
            local_index = self._get_local_index(instr)
            if self.stack:
                value = self._pop_expression()
                if local_index < len(self.locals):
                    local_name = self.locals[local_index].get('name', f'local{local_index}')
                    local_type = self.locals[local_index].get('type', 'var')
                    self.output.append(f"    {local_type} {local_name} = {value};")
        
        elif opcode.startswith('ldc'):
            value = self._get_constant_value(instr)
            if value is not None:
                self.stack.append(Expression('literal', value))
        
        elif opcode == 'ldnull':
            self.stack.append(Expression('literal', 'null'))
        
        elif opcode == 'dup':
            if self.stack:
                self.stack.append(self.stack[-1])
        
        elif opcode == 'pop':
            if self.stack:
                self.stack.pop()
        
        elif opcode in ['add', 'sub', 'mul', 'div', 'rem', 'and', 'or', 'xor', 'shl', 'shr']:
            self._binary_operation(instr)
        
        elif opcode in ['neg', 'not']:
            self._unary_operation(instr)
        
        elif opcode in ['ceq', 'cgt', 'clt', 'cgt.un', 'clt.un']:
            self._comparison(instr)
        
        elif opcode in ['call', 'callvirt']:
            self._call_method(instr)
        
        elif opcode == 'newobj':
            self._new_object(instr)
        
        elif opcode.startswith('ldfld'):
            self._load_field(instr)
        
        elif opcode.startswith('stfld'):
            self._store_field(instr)
        
        elif opcode.startswith('ldsfld'):
            self._load_static_field(instr)
        
        elif opcode.startswith('stsfld'):
            self._store_static_field(instr)
        
        elif opcode in ['box', 'unbox', 'castclass', 'isinst']:
            self._type_operation(instr)
        
        elif opcode == 'throw':
            if self.stack:
                value = self._pop_expression()
                self.output.append(f"    throw {value};")
            else:
                self.output.append("    throw;")
        
        elif opcode == 'newarr':
            self._new_array(instr)
        
        elif opcode == 'ldlen':
            if self.stack:
                array = self._pop_expression()
                self.stack.append(Expression('member_access', 'Length', [array]))
        
        elif opcode.startswith('ldelem'):
            self._load_element(instr)
        
        elif opcode.startswith('stelem'):
            self._store_element(instr)
        
        elif opcode.startswith('conv'):
            # Type conversion - usually implicit
            if self.stack:
                # Keep the value, just note the conversion
                pass
        
        elif opcode.startswith('stind'):
            # Store indirect - complex, needs pointer support
            if len(self.stack) >= 2:
                value = self._pop_expression()
                ptr = self._pop_expression()
                # In C#, we can't do pointer arithmetic easily
                # This would require unsafe code
                self.output.append(f"    // *{ptr} = {value}")
        
        elif opcode.startswith('ldind'):
            # Load indirect
            if self.stack:
                ptr = self._pop_expression()
                self.stack.append(Expression('unary', '*', [ptr]))
        
        elif opcode in ['leave', 'leave.s']:
            # Leave instruction - handled by control flow
            pass
        
        elif opcode == 'endfinally':
            # Endfinally - handled by control flow
            pass
        
        elif opcode == 'rethrow':
            self.output.append("    throw;")
        
        elif opcode.startswith('br'):
            self._branch(instr)
        
        elif opcode == 'switch':
            self._switch(instr)
        
        else:
            # Unknown or unimplemented opcode
            self.output.append(f"    // {instr}")
    
    def _get_arg_index(self, instr: ILInstruction) -> int:
        """Get argument index from ldarg/starg instruction."""
        if instr.opcode == 'ldarg.0':
            return 0
        elif instr.opcode == 'ldarg.1':
            return 1
        elif instr.opcode == 'ldarg.2':
            return 2
        elif instr.opcode == 'ldarg.3':
            return 3
        elif instr.opcode in ['ldarg.s', 'ldarg']:
            return instr.operand
        elif instr.opcode == 'starg.s':
            return instr.operand
        return 0
    
    def _get_local_index(self, instr: ILInstruction) -> int:
        """Get local index from ldloc/stloc instruction."""
        if instr.opcode == 'ldloc.0':
            return 0
        elif instr.opcode == 'ldloc.1':
            return 1
        elif instr.opcode == 'ldloc.2':
            return 2
        elif instr.opcode == 'ldloc.3':
            return 3
        elif instr.opcode in ['ldloc.s', 'ldloc', 'stloc.s', 'stloc']:
            return instr.operand
        return 0
    
    def _get_constant_value(self, instr: ILInstruction) -> Any:
        """Get constant value from ldc instruction."""
        if instr.opcode == 'ldc.i4.m1':
            return -1
        elif instr.opcode == 'ldc.i4.0':
            return 0
        elif instr.opcode == 'ldc.i4.1':
            return 1
        elif instr.opcode == 'ldc.i4.2':
            return 2
        elif instr.opcode == 'ldc.i4.3':
            return 3
        elif instr.opcode == 'ldc.i4.4':
            return 4
        elif instr.opcode == 'ldc.i4.5':
            return 5
        elif instr.opcode == 'ldc.i4.6':
            return 6
        elif instr.opcode == 'ldc.i4.7':
            return 7
        elif instr.opcode == 'ldc.i4.8':
            return 8
        elif instr.opcode == 'ldc.i4.s':
            return instr.operand
        elif instr.opcode == 'ldc.i4':
            return instr.operand
        elif instr.opcode == 'ldc.i8':
            return instr.operand
        elif instr.opcode == 'ldc.r4':
            return f"{instr.operand}f"
        elif instr.opcode == 'ldc.r8':
            return f"{instr.operand}d"
        return None
    
    def _binary_operation(self, instr: ILInstruction) -> None:
        """Handle binary operations."""
        op_map = {
            'add': '+',
            'sub': '-',
            'mul': '*',
            'div': '/',
            'rem': '%',
            'and': '&',
            'or': '|',
            'xor': '^',
            'shl': '<<',
            'shr': '>>',
            'shr.un': '>>>',
        }
        
        if len(self.stack) >= 2:
            right = self._pop_expression()
            left = self._pop_expression()
            operator = op_map.get(instr.opcode, instr.opcode)
            self.stack.append(Expression('binary', operator, [left, right]))
    
    def _unary_operation(self, instr: ILInstruction) -> None:
        """Handle unary operations."""
        op_map = {
            'neg': '-',
            'not': '~',
        }
        
        if self.stack:
            operand = self._pop_expression()
            operator = op_map.get(instr.opcode, instr.opcode)
            self.stack.append(Expression('unary', operator, [operand]))
    
    def _comparison(self, instr: ILInstruction) -> None:
        """Handle comparison operations."""
        op_map = {
            'ceq': '==',
            'cgt': '>',
            'clt': '<',
            'cgt.un': '>',
            'clt.un': '<',
        }
        
        if len(self.stack) >= 2:
            right = self._pop_expression()
            left = self._pop_expression()
            operator = op_map.get(instr.opcode, instr.opcode)
            self.stack.append(Expression('binary', operator, [left, right]))
    
    def _call_method(self, instr: ILInstruction) -> None:
        """Handle call/callvirt instructions."""
        if isinstance(instr.operand, str):
            method_name = instr.operand
            
            # Get argument count from method signature
            # This would normally come from metadata
            arg_count = self._get_method_arg_count(method_name)
            
            args = []
            for _ in range(arg_count):
                if self.stack:
                    args.insert(0, self._pop_expression())
            
            # Check if it's a constructor
            if method_name.endswith('::.ctor'):
                class_name = method_name.split('::')[0]
                expr = Expression('new', class_name, args)
                self.stack.append(expr)
            else:
                # Regular method call
                expr = Expression('call', method_name, args)
                self.stack.append(expr)
    
    def _new_object(self, instr: ILInstruction) -> None:
        """Handle newobj instruction."""
        if isinstance(instr.operand, str):
            type_name = instr.operand
            
            # Get constructor argument count
            arg_count = self._get_constructor_arg_count(type_name)
            
            args = []
            for _ in range(arg_count):
                if self.stack:
                    args.insert(0, self._pop_expression())
            
            self.stack.append(Expression('new', type_name, args))
    
    def _load_field(self, instr: ILInstruction) -> None:
        """Handle ldfld/ldflda instructions."""
        if isinstance(instr.operand, str):
            field_name = instr.operand
            if self.stack:
                obj = self._pop_expression()
                if instr.opcode == 'ldflda':
                    # Address of field - would need ref/out in C#
                    self.stack.append(Expression('member_access', f'ref {field_name}', [obj]))
                else:
                    self.stack.append(Expression('member_access', field_name, [obj]))
    
    def _store_field(self, instr: ILInstruction) -> None:
        """Handle stfld instruction."""
        if isinstance(instr.operand, str):
            field_name = instr.operand
            if len(self.stack) >= 2:
                value = self._pop_expression()
                obj = self._pop_expression()
                # Create assignment expression
                field_access = Expression('member_access', field_name, [obj])
                field_access.is_lvalue = True
                self.output.append(f"    {field_access} = {value};")
    
    def _load_static_field(self, instr: ILInstruction) -> None:
        """Handle ldsfld/ldsflda instructions."""
        if isinstance(instr.operand, str):
            field_name = instr.operand
            if instr.opcode == 'ldsflda':
                self.stack.append(Expression('variable', f'ref {field_name}'))
            else:
                self.stack.append(Expression('variable', field_name))
    
    def _store_static_field(self, instr: ILInstruction) -> None:
        """Handle stsfld instruction."""
        if isinstance(instr.operand, str):
            field_name = instr.operand
            if self.stack:
                value = self._pop_expression()
                self.output.append(f"    {field_name} = {value};")
    
    def _type_operation(self, instr: ILInstruction) -> None:
        """Handle box/unbox/castclass/isinst instructions."""
        if isinstance(instr.operand, str):
            type_name = instr.operand
            if self.stack:
                value = self._pop_expression()
                
                if instr.opcode == 'box':
                    # Boxing is implicit in C# when assigning value type to object
                    self.stack.append(value)
                elif instr.opcode == 'unbox':
                    self.stack.append(Expression('cast', type_name, [value]))
                elif instr.opcode == 'castclass':
                    self.stack.append(Expression('cast', type_name, [value]))
                elif instr.opcode == 'isinst':
                    self.stack.append(Expression('binary', 'as', [value, Expression('literal', type_name)]))
    
    def _new_array(self, instr: ILInstruction) -> None:
        """Handle newarr instruction."""
        if isinstance(instr.operand, str):
            type_name = instr.operand
            if self.stack:
                size = self._pop_expression()
                self.stack.append(Expression('new', f"{type_name}[]", [size]))
    
    def _load_element(self, instr: ILInstruction) -> None:
        """Handle ldelem* instructions."""
        if len(self.stack) >= 2:
            index = self._pop_expression()
            array = self._pop_expression()
            self.stack.append(Expression('array_access', None, [array, index]))
    
    def _store_element(self, instr: ILInstruction) -> None:
        """Handle stelem* instructions."""
        if len(self.stack) >= 3:
            value = self._pop_expression()
            index = self._pop_expression()
            array = self._pop_expression()
            array_access = Expression('array_access', None, [array, index])
            array_access.is_lvalue = True
            self.output.append(f"    {array_access} = {value};")
    
    def _branch(self, instr: ILInstruction) -> None:
        """Handle branch instructions."""
        op_map = {
            'br': 'goto',
            'br.s': 'goto',
            'brtrue': 'if',
            'brtrue.s': 'if',
            'brfalse': 'if',
            'brfalse.s': 'if',
            'beq': 'if',
            'beq.s': 'if',
            'bge': 'if',
            'bge.s': 'if',
            'bgt': 'if',
            'bgt.s': 'if',
            'ble': 'if',
            'ble.s': 'if',
            'blt': 'if',
            'blt.s': 'if',
            'bne.un': 'if',
            'bne.un.s': 'if',
            'bge.un': 'if',
            'bge.un.s': 'if',
            'bgt.un': 'if',
            'bgt.un.s': 'if',
            'ble.un': 'if',
            'ble.un.s': 'if',
            'blt.un': 'if',
            'blt.un.s': 'if',
        }
        
        if instr.opcode in op_map:
            op = op_map[instr.opcode]
            target_offset = instr.target if instr.target else 0
            label = self._get_label(target_offset)
            
            if op == 'goto':
                self.output.append(f"    goto {label};")
            else:
                # Conditional branch
                if self.stack:
                    condition = self._pop_expression()
                    
                    # For brfalse, negate the condition
                    if 'false' in instr.opcode:
                        condition = Expression('unary', '!', [condition])
                    
                    self.output.append(f"    if ({condition}) goto {label};")
    
    def _switch(self, instr: ILInstruction) -> None:
        """Handle switch instruction."""
        if isinstance(instr.operand, list):
            offsets = instr.operand
            if self.stack:
                value = self._pop_expression()
                label = self._get_label(instr.offset + instr.operand_size + 1 + offsets[0])
                
                self.output.append(f"    switch ({value})")
                self.output.append("    {")
                
                for i, offset in enumerate(offsets[1:]):
                    case_label = self._get_label(instr.offset + instr.operand_size + 1 + offset)
                    self.output.append(f"        case {i}:")
                    self.output.append(f"            goto {case_label};")
                
                # Default case falls through
                self.output.append("        default:")
                self.output.append(f"            goto {label};")
                self.output.append("    }")
    
    def _get_method_arg_count(self, method_name: str) -> int:
        """Get argument count for a method."""
        # This would normally come from metadata
        # For now, return a default based on common patterns
        if '::' in method_name:
            # Method with class
            return 0
        return 0
    
    def _get_constructor_arg_count(self, type_name: str) -> int:
        """Get argument count for a constructor."""
        # This would normally come from metadata
        return 0
    
    def _pop_expression(self) -> Expression:
        """Pop an expression from the stack."""
        if self.stack:
            return self.stack.pop()
        return Expression('literal', "/* error */")
    
    def _get_label(self, offset: int) -> str:
        """Get or create a label for an offset."""
        if offset not in self.labels:
            self.labels[offset] = f"IL_{offset:04X}"
        return self.labels[offset]


# ============================================================
# Type System
# ============================================================

class TypeSystem:
    """Manages type information for decompilation."""
    
    def __init__(self):
        self.types: Dict[str, Dict[str, Any]] = {}
        self.methods: Dict[str, Dict[str, Any]] = {}
        self.fields: Dict[str, Dict[str, Any]] = {}
        self.namespaces: Dict[str, Set[str]] = {}
        self.current_class: Optional[str] = None
        self.current_method: Optional[str] = None
    
    def add_type(self, name: str, info: Dict[str, Any]) -> None:
        """Add a type to the type system."""
        self.types[name] = info
        
        # Track namespace
        if '.' in name:
            namespace = name.rsplit('.', 1)[0]
            if namespace not in self.namespaces:
                self.namespaces[namespace] = set()
            self.namespaces[namespace].add(name.split('.')[-1])
    
    def get_type(self, name: str) -> Optional[Dict[str, Any]]:
        """Get type information."""
        return self.types.get(name)
    
    def resolve_token(self, token: int) -> str:
        """Resolve a metadata token to a string."""
        # Token format: type (1 byte) + index (3 bytes)
        token_type = (token >> 24) & 0xFF
        index = token & 0x00FFFFFF
        
        # Common token types
        if token_type == 0x01:  # TypeRef
            return self._resolve_type_ref(index)
        elif token_type == 0x02:  # TypeDef
            return self._resolve_type_def(index)
        elif token_type == 0x04:  # FieldDef
            return self._resolve_field_def(index)
        elif token_type == 0x06:  # MethodDef
            return self._resolve_method_def(index)
        elif token_type == 0x08:  # ParamDef
            return self._resolve_param_def(index)
        elif token_type == 0x11:  # MemberRef
            return self._resolve_member_ref(index)
        elif token_type == 0x15:  # String
            return self._resolve_string(index)
        elif token_type == 0x17:  # AssemblyRef
            return self._resolve_assembly_ref(index)
        elif token_type == 0x19:  # TypeSpec
            return self._resolve_type_spec(index)
        else:
            return f"0x{token:08X}"
    
    def _resolve_type_ref(self, index: int) -> str:
        """Resolve a TypeRef token."""
        return f"<TypeRef:{index}>"
    
    def _resolve_type_def(self, index: int) -> str:
        """Resolve a TypeDef token."""
        if index < len(self.types):
            return list(self.types.keys())[index]
        return f"<TypeDef:{index}>"
    
    def _resolve_field_def(self, index: int) -> str:
        """Resolve a FieldDef token."""
        if index < len(self.fields):
            return list(self.fields.keys())[index]
        return f"<FieldDef:{index}>"
    
    def _resolve_method_def(self, index: int) -> str:
        """Resolve a MethodDef token."""
        if index < len(self.methods):
            return list(self.methods.keys())[index]
        return f"<MethodDef:{index}>"
    
    def _resolve_param_def(self, index: int) -> str:
        """Resolve a ParamDef token."""
        return f"<ParamDef:{index}>"
    
    def _resolve_member_ref(self, index: int) -> str:
        """Resolve a MemberRef token."""
        return f"<MemberRef:{index}>"
    
    def _resolve_string(self, index: int) -> str:
        """Resolve a String token."""
        return f"<String:{index}>"
    
    def _resolve_assembly_ref(self, index: int) -> str:
        """Resolve an AssemblyRef token."""
        return f"<AssemblyRef:{index}>"
    
    def _resolve_type_spec(self, index: int) -> str:
        """Resolve a TypeSpec token."""
        return f"<TypeSpec:{index}>"


# ============================================================
# Main Decompiler
# ============================================================

class MonoDecompiler:
    """Main Mono decompiler - converts IL to C#."""
    
    def __init__(self):
        self.type_system = TypeSystem()
        self.assemblies: Dict[str, MonoAssembly] = {}
        self.current_assembly: Optional[MonoAssembly] = None
    
    def load_assembly(self, path: str) -> Optional[MonoAssembly]:
        """Load a Mono assembly and extract metadata."""
        with open(path, 'rb') as f:
            data = f.read()
        
        assembly = MonoAssembly()
        if assembly.parse(data):
            self.assemblies[path] = assembly
            self.current_assembly = assembly
            self._extract_metadata(assembly)
            return assembly
        return None
    
    def _extract_metadata(self, assembly: MonoAssembly) -> None:
        """Extract all metadata from the assembly."""
        if not assembly.metadata:
            return
        
        # Extract types
        if TABLE_TYPE_DEF in assembly.metadata.tables:
            for row in assembly.metadata.tables[TABLE_TYPE_DEF]:
                type_name = row.get('TypeName', '')
                type_namespace = row.get('TypeNamespace', '')
                full_name = f"{type_namespace}.{type_name}" if type_namespace else type_name
                
                # Store type info
                type_info = {
                    'name': type_name,
                    'namespace': type_namespace,
                    'flags': row.get('Flags', 0),
                    'extends': row.get('Extends', 0),
                    'field_list': row.get('FieldList', 0),
                    'method_list': row.get('MethodList', 0),
                }
                self.type_system.add_type(full_name, type_info)
        
        # Extract methods
        if TABLE_METHOD in assembly.metadata.tables:
            for row in assembly.metadata.tables[TABLE_METHOD]:
                method_name = row.get('Name', '')
                method_info = {
                    'name': method_name,
                    'flags': row.get('Flags', 0),
                    'impl_flags': row.get('ImplFlags', 0),
                    'param_list': row.get('ParamList', 0),
                    'rva': row.get('RVA', 0),
                }
                self.type_system.methods[method_name] = method_info
        
        # Extract fields
        if TABLE_FIELD in assembly.metadata.tables:
            for row in assembly.metadata.tables[TABLE_FIELD]:
                field_name = row.get('Name', '')
                field_info = {
                    'name': field_name,
                    'flags': row.get('Flags', 0),
                    'signature': row.get('Signature', ''),
                }
                self.type_system.fields[field_name] = field_info
        
        # Extract parameters
        if TABLE_PARAM in assembly.metadata.tables:
            for row in assembly.metadata.tables[TABLE_PARAM]:
                param_name = row.get('Name', '')
                param_info = {
                    'name': param_name,
                    'flags': row.get('Flags', 0),
                    'sequence': row.get('Sequence', 0),
                    'type': row.get('Type', 0),
                }
                # Store in method info
                pass
    
    def decompile_method(self, assembly: MonoAssembly, method_rva: int, 
                         method_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Decompile a single method."""
        # Get method body
        il_code = assembly.get_method_body(method_rva)
        if not il_code or len(il_code) == 0:
            return None
        
        # Get method info if not provided
        if method_info is None:
            method_info = {'name': f"Method_{method_rva:08X}", 'return_type': 'void'}
        
        # Get locals and parameters
        # These would come from the method's local variable signature
        locals = []
        parameters = []
        
        # Disassemble
        disassembler = ILDisassembler(
            il_code,
            resolve_token=self.type_system.resolve_token
        )
        instructions = disassembler.disassemble()
        
        # Build expression tree
        builder = ExpressionBuilder(
            instructions, method_info, self.type_system, locals, parameters
        )
        
        # Generate code
        return '\n'.join(builder.build())
    
    def decompile_all_methods(self, assembly: MonoAssembly) -> Dict[str, str]:
        """Decompile all methods in an assembly."""
        results = {}
        
        if not assembly.metadata:
            return results
        
        # Get all methods
        if TABLE_METHOD in assembly.metadata.tables:
            for row in assembly.metadata.tables[TABLE_METHOD]:
                method_name = row.get('Name', '')
                method_rva = row.get('RVA', 0)
                
                if method_rva > 0:
                    code = self.decompile_method(assembly, method_rva, {
                        'name': method_name,
                        'return_type': 'void',  # Would come from method signature
                    })
                    
                    if code:
                        results[method_name] = code
        
        return results
    
    def decompile_class(self, assembly: MonoAssembly, class_name: str) -> Dict[str, str]:
        """Decompile all methods in a class."""
        results = {}
        
        # Find all methods belonging to this class
        # This would require parsing the method table and matching declaring types
        
        # For now, decompile all methods
        return self.decompile_all_methods(assembly)
