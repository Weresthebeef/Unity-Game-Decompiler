"""
Mono IL disassembler and decompiler.
Converts CIL (Common Intermediate Language) to readable C# code.
"""
import struct
from typing import Dict, List, Optional, Any, Tuple, Callable
from .pe import MonoAssembly
from ..utils import Reader


# ============================================================
# IL Opcodes
# ============================================================

# Opcode table: (name, operand_type, operand_size, stack_effect)
# operand_type: None, int8, int16, int32, int64, uint8, uint16, uint32, uint64, type, method, field, token, string, switch
IL_OPCODES = [
    # 0x00-0x0F
    ("nop", None, 0, (0, 0)),
    ("break", None, 0, (0, 0)),
    ("ldarg.0", None, 0, (0, 1)),
    ("ldarg.1", None, 0, (0, 1)),
    ("ldarg.2", None, 0, (0, 1)),
    ("ldarg.3", None, 0, (0, 1)),
    ("ldloc.0", None, 0, (0, 1)),
    ("ldloc.1", None, 0, (0, 1)),
    ("ldloc.2", None, 0, (0, 1)),
    ("ldloc.3", None, 0, (0, 1)),
    ("stloc.0", None, 0, (1, 0)),
    ("stloc.1", None, 0, (1, 0)),
    ("stloc.2", None, 0, (1, 0)),
    ("stloc.3", None, 0, (1, 0)),
    ("ldarg.s", "uint8", 1, (0, 1)),
    ("ldarga.s", "uint8", 1, (0, 1)),
    
    # 0x10-0x1F
    ("starg.s", "uint8", 1, (1, 0)),
    ("ldloc.s", "uint8", 1, (0, 1)),
    ("ldloca.s", "uint8", 1, (0, 1)),
    ("stloc.s", "uint8", 1, (1, 0)),
    ("ldnull", None, 0, (0, 1)),
    ("ldc.i4.m1", None, 0, (0, 1)),
    ("ldc.i4.0", None, 0, (0, 1)),
    ("ldc.i4.1", None, 0, (0, 1)),
    ("ldc.i4.2", None, 0, (0, 1)),
    ("ldc.i4.3", None, 0, (0, 1)),
    ("ldc.i4.4", None, 0, (0, 1)),
    ("ldc.i4.5", None, 0, (0, 1)),
    ("ldc.i4.6", None, 0, (0, 1)),
    ("ldc.i4.7", None, 0, (0, 1)),
    ("ldc.i4.8", None, 0, (0, 1)),
    
    # 0x20-0x2F
    ("ldc.i4.s", "int8", 1, (0, 1)),
    ("ldc.i4", "int32", 4, (0, 1)),
    ("ldc.i8", "int64", 8, (0, 1)),
    ("ldc.r4", "float32", 4, (0, 1)),
    ("ldc.r8", "float64", 8, (0, 1)),
    ("dup", None, 0, (1, 2)),
    ("pop", None, 0, (1, 0)),
    ("jmp", "method", 4, (0, 0)),
    ("call", "method", 4, (-1, 1)),
    ("calli", "method", 4, (-1, 1)),
    ("ret", None, 0, (-1, 0)),
    ("br.s", "int8", 1, (0, 0)),
    ("brfalse.s", "int8", 1, (1, 0)),
    ("brtrue.s", "int8", 1, (1, 0)),
    
    # 0x30-0x3F
    ("beq.s", "int8", 1, (2, 0)),
    ("bge.s", "int8", 1, (2, 0)),
    ("bgt.s", "int8", 1, (2, 0)),
    ("ble.s", "int8", 1, (2, 0)),
    ("blt.s", "int8", 1, (2, 0)),
    ("bne.un.s", "int8", 1, (2, 0)),
    ("bge.un.s", "int8", 1, (2, 0)),
    ("bgt.un.s", "int8", 1, (2, 0)),
    ("ble.un.s", "int8", 1, (2, 0)),
    ("blt.un.s", "int8", 1, (2, 0)),
    ("br", "int32", 4, (0, 0)),
    ("brfalse", "int32", 4, (1, 0)),
    ("brtrue", "int32", 4, (1, 0)),
    ("beq", "int32", 4, (2, 0)),
    ("bge", "int32", 4, (2, 0)),
    
    # 0x40-0x4F
    ("bgt", "int32", 4, (2, 0)),
    ("ble", "int32", 4, (2, 0)),
    ("blt", "int32", 4, (2, 0)),
    ("bne.un", "int32", 4, (2, 0)),
    ("bge.un", "int32", 4, (2, 0)),
    ("bgt.un", "int32", 4, (2, 0)),
    ("ble.un", "int32", 4, (2, 0)),
    ("blt.un", "int32", 4, (2, 0)),
    ("switch", "switch", -1, (1, 0)),
    ("ldind.i1", None, 0, (0, 1)),
    ("ldind.u1", None, 0, (0, 1)),
    ("ldind.i2", None, 0, (0, 1)),
    ("ldind.u2", None, 0, (0, 1)),
    ("ldind.i4", None, 0, (0, 1)),
    ("ldind.u4", None, 0, (0, 1)),
    
    # 0x50-0x5F
    ("ldind.i8", None, 0, (0, 1)),
    ("ldind.r4", None, 0, (0, 1)),
    ("ldind.r8", None, 0, (0, 1)),
    ("ldind.ref", None, 0, (0, 1)),
    ("stind.ref", None, 0, (2, 0)),
    ("stind.i1", None, 0, (2, 0)),
    ("stind.i2", None, 0, (2, 0)),
    ("stind.i4", None, 0, (2, 0)),
    ("stind.i8", None, 0, (2, 0)),
    ("stind.r4", None, 0, (2, 0)),
    ("stind.r8", None, 0, (2, 0)),
    ("add", None, 0, (2, 1)),
    ("sub", None, 0, (2, 1)),
    ("mul", None, 0, (2, 1)),
    ("div", None, 0, (2, 1)),
    ("rem", None, 0, (2, 1)),
    
    # 0x60-0x6F
    ("and", None, 0, (2, 1)),
    ("or", None, 0, (2, 1)),
    ("xor", None, 0, (2, 1)),
    ("shl", None, 0, (2, 1)),
    ("shr", None, 0, (2, 1)),
    ("shr.un", None, 0, (2, 1)),
    ("neg", None, 0, (1, 1)),
    ("not", None, 0, (1, 1)),
    ("conv.i1", None, 0, (1, 1)),
    ("conv.i2", None, 0, (1, 1)),
    ("conv.i4", None, 0, (1, 1)),
    ("conv.i8", None, 0, (1, 1)),
    ("conv.r4", None, 0, (1, 1)),
    ("conv.r8", None, 0, (1, 1)),
    ("conv.u4", None, 0, (1, 1)),
    ("conv.u8", None, 0, (1, 1)),
    
    # 0x70-0x7F
    ("callvirt", "method", 4, (-1, 1)),
    ("cpobj", "type", 4, (1, 1)),
    ("ldobj", "type", 4, (0, 1)),
    ("ldstr", "string", 4, (0, 1)),
    ("newobj", "method", 4, (-1, 1)),
    ("castclass", "type", 4, (1, 1)),
    ("isinst", "type", 4, (1, 1)),
    ("conv.r.un", None, 0, (1, 1)),
    ("unbox", "type", 4, (1, 1)),
    ("throw", None, 0, (1, 0)),
    ("ldfld", "field", 4, (1, 1)),
    ("ldflda", "field", 4, (1, 1)),
    ("stfld", "field", 4, (2, 0)),
    ("ldsfld", "field", 4, (0, 1)),
    ("ldsflda", "field", 4, (0, 1)),
    
    # 0x80-0x8F
    ("stsfld", "field", 4, (1, 0)),
    ("stobj", "type", 4, (2, 0)),
    ("conv.ovf.i1.un", None, 0, (1, 1)),
    ("conv.ovf.i2.un", None, 0, (1, 1)),
    ("conv.ovf.i4.un", None, 0, (1, 1)),
    ("conv.ovf.i8.un", None, 0, (1, 1)),
    ("conv.ovf.u1.un", None, 0, (1, 1)),
    ("conv.ovf.u2.un", None, 0, (1, 1)),
    ("conv.ovf.u4.un", None, 0, (1, 1)),
    ("conv.ovf.u8.un", None, 0, (1, 1)),
    ("conv.ovf.i1", None, 0, (1, 1)),
    ("conv.ovf.u1", None, 0, (1, 1)),
    ("conv.ovf.i2", None, 0, (1, 1)),
    ("conv.ovf.u2", None, 0, (1, 1)),
    ("conv.ovf.i4", None, 0, (1, 1)),
    ("conv.ovf.u4", None, 0, (1, 1)),
    
    # 0x90-0x9F
    ("conv.ovf.i8", None, 0, (1, 1)),
    ("conv.ovf.u8", None, 0, (1, 1)),
    ("refanyval", "type", 4, (1, 1)),
    ("ckfinite", None, 0, (1, 1)),
    ("mkrefany", "type", 4, (1, 1)),
    ("ldtoken", "token", 4, (0, 1)),
    ("conv.u2", None, 0, (1, 1)),
    ("conv.u1", None, 0, (1, 1)),
    ("conv.i", None, 0, (1, 1)),
    ("conv.ovf.i", None, 0, (1, 1)),
    ("conv.ovf.u", None, 0, (1, 1)),
    ("add.ovf", None, 0, (2, 1)),
    ("add.ovf.un", None, 0, (2, 1)),
    ("mul.ovf", None, 0, (2, 1)),
    ("mul.ovf.un", None, 0, (2, 1)),
    
    # 0xA0-0xAF
    ("sub.ovf", None, 0, (2, 1)),
    ("sub.ovf.un", None, 0, (2, 1)),
    ("endfinally", None, 0, (0, 0)),
    ("leave", "int32", 4, (0, 0)),
    ("leave.s", "int8", 1, (0, 0)),
    ("stind.i", None, 0, (2, 0)),
    ("conv.u", None, 0, (1, 1)),
    ("arglist", None, 0, (0, 1)),
    ("ceq", None, 0, (2, 1)),
    ("cgt", None, 0, (2, 1)),
    ("cgt.un", None, 0, (2, 1)),
    ("clt", None, 0, (2, 1)),
    ("clt.un", None, 0, (2, 1)),
    ("cgt", None, 0, (2, 1)),
    ("cgt.un", None, 0, (2, 1)),
    
    # 0xB0-0xBF
    ("box", "type", 4, (1, 1)),
    ("newarr", "type", 4, (0, 1)),
    ("ldlen", None, 0, (1, 1)),
    ("ldelem.i1", None, 0, (2, 1)),
    ("ldelem.u1", None, 0, (2, 1)),
    ("ldelem.i2", None, 0, (2, 1)),
    ("ldelem.u2", None, 0, (2, 1)),
    ("ldelem.i4", None, 0, (2, 1)),
    ("ldelem.u4", None, 0, (2, 1)),
    ("ldelem.i8", None, 0, (2, 1)),
    ("ldelem.r4", None, 0, (2, 1)),
    ("ldelem.r8", None, 0, (2, 1)),
    ("ldelem.ref", None, 0, (2, 1)),
    ("stelem.i", None, 0, (3, 0)),
    ("stelem.i1", None, 0, (3, 0)),
    ("stelem.i2", None, 0, (3, 0)),
    
    # 0xC0-0xCF
    ("stelem.i4", None, 0, (3, 0)),
    ("stelem.i8", None, 0, (3, 0)),
    ("stelem.r4", None, 0, (3, 0)),
    ("stelem.r8", None, 0, (3, 0)),
    ("stelem.ref", None, 0, (3, 0)),
    ("ldelem.any", "type", 4, (2, 1)),
    ("stelem.any", "type", 4, (3, 0)),
    ("unbox.any", "type", 4, (1, 1)),
    ("conv.ovf.i1.un", None, 0, (1, 1)),
    ("conv.ovf.i2.un", None, 0, (1, 1)),
    ("conv.ovf.i4.un", None, 0, (1, 1)),
    ("conv.ovf.i8.un", None, 0, (1, 1)),
    ("conv.ovf.u1.un", None, 0, (1, 1)),
    ("conv.ovf.u2.un", None, 0, (1, 1)),
    ("conv.ovf.u4.un", None, 0, (1, 1)),
    ("conv.ovf.u8.un", None, 0, (1, 1)),
    
    # 0xD0-0xDF
    ("conv.ovf.i.un", None, 0, (1, 1)),
    ("conv.ovf.u.un", None, 0, (1, 1)),
    ("box", "type", 4, (1, 1)),
    ("newarr", "type", 4, (0, 1)),
    ("ldlen", None, 0, (1, 1)),
    ("ldelem.i1", None, 0, (2, 1)),
    ("ldelem.u1", None, 0, (2, 1)),
    ("ldelem.i2", None, 0, (2, 1)),
    ("ldelem.u2", None, 0, (2, 1)),
    ("ldelem.i4", None, 0, (2, 1)),
    ("ldelem.u4", None, 0, (2, 1)),
    ("ldelem.i8", None, 0, (2, 1)),
    ("ldelem.r4", None, 0, (2, 1)),
    ("ldelem.r8", None, 0, (2, 1)),
    ("ldelem.ref", None, 0, (2, 1)),
    
    # 0xE0-0xEF
    ("stelem.i", None, 0, (3, 0)),
    ("stelem.i1", None, 0, (3, 0)),
    ("stelem.i2", None, 0, (3, 0)),
    ("stelem.i4", None, 0, (3, 0)),
    ("stelem.i8", None, 0, (3, 0)),
    ("stelem.r4", None, 0, (3, 0)),
    ("stelem.r8", None, 0, (3, 0)),
    ("stelem.ref", None, 0, (3, 0)),
    ("ldelem.any", "type", 4, (2, 1)),
    ("stelem.any", "type", 4, (3, 0)),
    ("unbox.any", "type", 4, (1, 1)),
    ("conv.ovf.i1.un", None, 0, (1, 1)),
    ("conv.ovf.i2.un", None, 0, (1, 1)),
    ("conv.ovf.i4.un", None, 0, (1, 1)),
    
    # 0xF0-0xFF
    ("conv.ovf.i8.un", None, 0, (1, 1)),
    ("conv.ovf.u1.un", None, 0, (1, 1)),
    ("conv.ovf.u2.un", None, 0, (1, 1)),
    ("conv.ovf.u4.un", None, 0, (1, 1)),
    ("conv.ovf.u8.un", None, 0, (1, 1)),
    ("conv.ovf.i.un", None, 0, (1, 1)),
    ("conv.ovf.u.un", None, 0, (1, 1)),
    ("ldnull", None, 0, (0, 1)),
    ("ldc.i4.m1", None, 0, (0, 1)),
    ("ldc.i4.0", None, 0, (0, 1)),
    ("ldc.i4.1", None, 0, (0, 1)),
    ("ldc.i4.2", None, 0, (0, 1)),
    ("ldc.i4.3", None, 0, (0, 1)),
    ("ldc.i4.4", None, 0, (0, 1)),
    ("ldc.i4.5", None, 0, (0, 1)),
    ("ldc.i4.6", None, 0, (0, 1)),
    ("ldc.i4.7", None, 0, (0, 1)),
    ("ldc.i4.8", None, 0, (0, 1)),
]

# Prefixed opcodes (0xFE)
PREFIXED_OPCODES = {
    0x00: ("arglist", None, 0),
    0x01: ("ceq", None, 0),
    0x02: ("cgt", None, 0),
    0x03: ("cgt.un", None, 0),
    0x04: ("clt", None, 0),
    0x05: ("clt.un", None, 0),
    0x06: ("ldftn", "method", 4),
    0x07: ("ldvirtftn", "method", 4),
    0x08: ("ldarg", "uint16", 2),
    0x09: ("ldarga", "uint16", 2),
    0x0A: ("starg", "uint16", 2),
    0x0B: ("ldloc", "uint16", 2),
    0x0C: ("ldloca", "uint16", 2),
    0x0D: ("stloc", "uint16", 2),
    0x0E: ("localloc", None, 0),
    0x0F: ("endfilter", None, 0),
    0x10: ("unaligned.", None, 1),  # Followed by alignment byte
    0x11: ("volatile.", None, 0),
    0x12: ("tail.", None, 0),
    0x13: ("initobj", "type", 4),
    0x14: ("constrained.", "type", 4),
    0x15: ("cpblk", None, 0),
    0x16: ("initblk", None, 0),
    0x17: ("rethrow", None, 0),
    0x18: ("sizeof", "type", 4),
    0x19: ("refanytype", None, 0),
    0x1A: ("readonly.", None, 0),
}


# ============================================================
# IL Instruction
# ============================================================

class ILInstruction:
    """Represents a single IL instruction."""
    __slots__ = ('offset', 'opcode', 'operand', 'operand_type', 'operand_size', 'stack_before', 'stack_after')
    
    def __init__(self, offset: int, opcode: str, operand: Any = None, operand_type: str = '', operand_size: int = 0):
        self.offset = offset
        self.opcode = opcode
        self.operand = operand
        self.operand_type = operand_type
        self.operand_size = operand_size
        self.stack_before = 0
        self.stack_after = 0
    
    def __repr__(self):
        if self.operand is not None:
            return f"{self.offset:04X}: {self.opcode} {self.operand}"
        return f"{self.offset:04X}: {self.opcode}"


# ============================================================
# IL Disassembler
# ============================================================

class ILDisassembler:
    """Disassemble IL bytecode into instructions."""
    
    def __init__(self, il_code: bytes, resolve_token: Optional[Callable[[int], str]] = None):
        self.il_code = il_code
        self.resolve_token = resolve_token
        self.instructions: List[ILInstruction] = []
        self.exception_handlers: List[Dict[str, Any]] = []
    
    def disassemble(self) -> List[ILInstruction]:
        """Disassemble IL code into instructions."""
        reader = Reader(self.il_code, '<')
        self.instructions = []
        
        while reader.remaining() > 0:
            offset = reader.tell()
            opcode_byte = reader.read_u8()
            
            # Check for prefixed opcode
            if opcode_byte == 0xFE:
                prefix_byte = reader.read_u8()
                if prefix_byte in PREFIXED_OPCODES:
                    name, op_type, op_size = PREFIXED_OPCODES[prefix_byte]
                    if name == "unaligned.":
                        alignment = reader.read_u8()
                        name = f"unaligned.{alignment}"
                        op_type = None
                        op_size = 0
                    elif name == "constrained.":
                        token = reader.read_u32()
                        type_name = self.resolve_token(token) if self.resolve_token else f"0x{token:08X}"
                        name = f"constrained. {type_name}"
                        op_type = None
                        op_size = 0
                    elif name == "initobj" or name == "sizeof" or name == "ldftn" or name == "ldvirtftn":
                        token = reader.read_u32()
                        resolved = self.resolve_token(token) if self.resolve_token else f"0x{token:08X}"
                        self.instructions.append(ILInstruction(offset, name, resolved, op_type, op_size))
                        continue
                    elif op_type == "uint16":
                        operand = reader.read_u16()
                        self.instructions.append(ILInstruction(offset, name, operand, op_type, op_size))
                        continue
                    elif op_type == "method" or op_type == "type":
                        token = reader.read_u32()
                        resolved = self.resolve_token(token) if self.resolve_token else f"0x{token:08X}"
                        self.instructions.append(ILInstruction(offset, name, resolved, op_type, op_size))
                        continue
                    else:
                        self.instructions.append(ILInstruction(offset, name, None, op_type, op_size))
                        continue
                else:
                    # Unknown prefixed opcode
                    self.instructions.append(ILInstruction(offset, f"fe.{prefix_byte:02X}", None))
                    continue
            
            # Regular opcode
            if opcode_byte >= len(IL_OPCODES):
                self.instructions.append(ILInstruction(offset, f"unknown_{opcode_byte:02X}", None))
                continue
            
            name, op_type, op_size, stack_effect = IL_OPCODES[opcode_byte]
            
            if op_type is None:
                self.instructions.append(ILInstruction(offset, name, None, op_type, 0))
            elif op_type == "int8":
                operand = reader.read_i8()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 1))
            elif op_type == "uint8":
                operand = reader.read_u8()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 1))
            elif op_type == "int16":
                operand = reader.read_i16()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 2))
            elif op_type == "uint16":
                operand = reader.read_u16()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 2))
            elif op_type == "int32":
                operand = reader.read_i32()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 4))
            elif op_type == "uint32":
                operand = reader.read_u32()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 4))
            elif op_type == "int64":
                operand = reader.read_i64()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 8))
            elif op_type == "uint64":
                operand = reader.read_u64()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 8))
            elif op_type == "float32":
                operand = reader.read_float()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 4))
            elif op_type == "float64":
                operand = reader.read_double()
                self.instructions.append(ILInstruction(offset, name, operand, op_type, 8))
            elif op_type == "method" or op_type == "field" or op_type == "type" or op_type == "token":
                token = reader.read_u32()
                resolved = self.resolve_token(token) if self.resolve_token else f"0x{token:08X}"
                self.instructions.append(ILInstruction(offset, name, resolved, op_type, 4))
            elif op_type == "string":
                token = reader.read_u32()
                resolved = self.resolve_token(token) if self.resolve_token else f"0x{token:08X}"
                self.instructions.append(ILInstruction(offset, name, f'"{resolved}"', op_type, 4))
            elif op_type == "switch":
                # Switch opcode: read count, then count * 4 bytes of offsets
                count = reader.read_u32()
                offsets = [reader.read_u32() for _ in range(count)]
                self.instructions.append(ILInstruction(offset, name, offsets, op_type, 4 + count * 4))
            else:
                self.instructions.append(ILInstruction(offset, name, None, op_type, 0))
        
        return self.instructions


# ============================================================
# IL Decompiler
# ============================================================

class ILDecompiler:
    """Decompile IL instructions to C#-like code."""
    
    def __init__(self, instructions: List[ILInstruction], method_info: Optional[Dict[str, Any]] = None):
        self.instructions = instructions
        self.method_info = method_info or {}
        self.locals: List[Dict[str, Any]] = []
        self.parameters: List[Dict[str, Any]] = []
        self.labels: Dict[int, str] = {}
        self.blocks: List[List[ILInstruction]] = []
        self.current_block: List[ILInstruction] = []
        self.output: List[str] = []
    
    def decompile(self, locals: List[Dict[str, Any]] = None, parameters: List[Dict[str, Any]] = None) -> str:
        """Decompile IL to C#-like code."""
        if locals:
            self.locals = locals
        if parameters:
            self.parameters = parameters
        
        # Analyze control flow
        self._analyze_control_flow()
        
        # Generate code
        self._generate_code()
        
        return '\n'.join(self.output)
    
    def _analyze_control_flow(self) -> None:
        """Identify basic blocks and control flow."""
        # Find branch targets
        targets = set()
        for instr in self.instructions:
            if instr.opcode in ['br', 'brtrue', 'brfalse', 'beq', 'bge', 'bgt', 'ble', 'blt',
                               'bne.un', 'bge.un', 'bgt.un', 'ble.un', 'blt.un',
                               'br.s', 'brtrue.s', 'brfalse.s', 'beq.s', 'bge.s', 'bgt.s',
                               'ble.s', 'blt.s', 'bne.un.s', 'bge.un.s', 'bgt.un.s',
                               'ble.un.s', 'blt.un.s']:
                if isinstance(instr.operand, int):
                    targets.add(instr.offset + instr.operand)
                elif isinstance(instr.operand, list):
                    for offset in instr.operand:
                        targets.add(instr.offset + offset)
        
        # Also add exception handler targets
        # (Would need exception table from method header)
        
        # Identify block boundaries
        boundaries = {0}
        for instr in self.instructions:
            if instr.offset in targets:
                boundaries.add(instr.offset)
            if instr.opcode in ['ret', 'throw', 'br', 'leave']:
                boundaries.add(instr.offset + instr.operand_size + (1 if instr.operand_size > 0 else 0))
        
        # Create basic blocks
        self.blocks = []
        current_block = []
        for instr in self.instructions:
            if instr.offset in boundaries and current_block:
                self.blocks.append(current_block)
                current_block = []
            current_block.append(instr)
        
        if current_block:
            self.blocks.append(current_block)
    
    def _generate_code(self) -> None:
        """Generate C#-like code from basic blocks."""
        # Write method signature
        method_name = self.method_info.get('name', 'Method')
        return_type = self.method_info.get('return_type', 'void')
        
        # Build parameter list
        param_list = []
        for param in self.parameters:
            param_type = param.get('type', 'object')
            param_name = param.get('name', f'arg{len(param_list)}')
            param_list.append(f"{param_type} {param_name}")
        
        # Method signature
        self.output.append(f"{return_type} {method_name}({', '.join(param_list)})")
        self.output.append("{")
        
        # Process each block
        for i, block in enumerate(self.blocks):
            self._generate_block_code(block, i)
        
        self.output.append("}")
    
    def _generate_block_code(self, block: List[ILInstruction], block_index: int) -> None:
        """Generate code for a single basic block."""
        # Check if this is a branch target
        is_target = any(instr.offset in self.labels for instr in block)
        
        # Generate label if needed
        if is_target and block:
            label_name = self._get_label_name(block[0].offset)
            self.output.append(f"{label_name}:")
        
        # Generate expressions for each instruction
        for instr in block:
            self._generate_instruction_code(instr)
    
    def _generate_instruction_code(self, instr: ILInstruction) -> None:
        """Generate C# code for a single instruction."""
        opcode = instr.opcode
        
        # Handle special opcodes
        if opcode == 'nop':
            return
        elif opcode == 'ret':
            self.output.append("    return;")
            return
        elif opcode.startswith('ldarg'):
            self._load_arg(instr)
        elif opcode.startswith('ldloc'):
            self._load_local(instr)
        elif opcode.startswith('stloc'):
            self._store_local(instr)
        elif opcode.startswith('ldc'):
            self._load_constant(instr)
        elif opcode.startswith('call') or opcode.startswith('callvirt'):
            self._call_method(instr)
        elif opcode.startswith('newobj'):
            self._new_object(instr)
        elif opcode.startswith('ldfld'):
            self._load_field(instr)
        elif opcode.startswith('stfld'):
            self._store_field(instr)
        elif opcode in ['add', 'sub', 'mul', 'div', 'rem']:
            self._binary_operation(instr)
        elif opcode in ['and', 'or', 'xor', 'shl', 'shr']:
            self._binary_operation(instr)
        elif opcode == 'neg':
            self._unary_operation(instr, '-')
        elif opcode == 'not':
            self._unary_operation(instr, '~')
        elif opcode in ['ceq', 'cgt', 'clt', 'cgt.un', 'clt.un']:
            self._comparison(instr)
        elif opcode in ['br', 'brtrue', 'brfalse', 'beq', 'bge', 'bgt', 'ble', 'blt']:
            self._branch(instr)
        elif opcode == 'dup':
            # DUP is handled by the stack machine
            pass
        elif opcode == 'pop':
            # POP is handled by the stack machine
            pass
        elif opcode.startswith('conv'):
            # Type conversion - handled implicitly
            pass
        elif opcode == 'box':
            # Boxing - handled implicitly
            pass
        elif opcode == 'unbox':
            # Unboxing - handled implicitly
            pass
        elif opcode == 'castclass':
            # Type cast - handled implicitly
            pass
        elif opcode == 'isinst':
            self._is_inst(instr)
        elif opcode == 'throw':
            self.output.append("    throw;")
        elif opcode == 'newarr':
            self._new_array(instr)
        elif opcode == 'ldlen':
            self._load_length(instr)
        elif opcode.startswith('ldelem'):
            self._load_element(instr)
        elif opcode.startswith('stelem'):
            self._store_element(instr)
        elif opcode == 'ldnull':
            self.output.append("    // ldnull")
        elif opcode.startswith('stind'):
            # Store indirect - complex
            pass
        elif opcode.startswith('ldind'):
            # Load indirect - complex
            pass
        elif opcode == 'leave':
            self.output.append("    // leave")
        elif opcode == 'endfinally':
            self.output.append("    // endfinally")
        else:
            self.output.append(f"    // {instr}")
    
    def _load_arg(self, instr: ILInstruction) -> None:
        """Handle ldarg* instructions."""
        if instr.opcode == 'ldarg.0':
            arg_index = 0
        elif instr.opcode == 'ldarg.1':
            arg_index = 1
        elif instr.opcode == 'ldarg.2':
            arg_index = 2
        elif instr.opcode == 'ldarg.3':
            arg_index = 3
        elif instr.opcode == 'ldarg.s':
            arg_index = instr.operand
        elif instr.opcode == 'ldarg':
            arg_index = instr.operand
        else:
            return
        
        if arg_index < len(self.parameters):
            arg_name = self.parameters[arg_index].get('name', f'arg{arg_index}')
            self.output.append(f"    // push {arg_name}")
        else:
            self.output.append(f"    // push arg[{arg_index}]")
    
    def _load_local(self, instr: ILInstruction) -> None:
        """Handle ldloc* instructions."""
        if instr.opcode == 'ldloc.0':
            local_index = 0
        elif instr.opcode == 'ldloc.1':
            local_index = 1
        elif instr.opcode == 'ldloc.2':
            local_index = 2
        elif instr.opcode == 'ldloc.3':
            local_index = 3
        elif instr.opcode == 'ldloc.s':
            local_index = instr.operand
        elif instr.opcode == 'ldloc':
            local_index = instr.operand
        else:
            return
        
        if local_index < len(self.locals):
            local_name = self.locals[local_index].get('name', f'local{local_index}')
            self.output.append(f"    // push {local_name}")
        else:
            self.output.append(f"    // push local[{local_index}]")
    
    def _store_local(self, instr: ILInstruction) -> None:
        """Handle stloc* instructions."""
        if instr.opcode == 'stloc.0':
            local_index = 0
        elif instr.opcode == 'stloc.1':
            local_index = 1
        elif instr.opcode == 'stloc.2':
            local_index = 2
        elif instr.opcode == 'stloc.3':
            local_index = 3
        elif instr.opcode == 'stloc.s':
            local_index = instr.operand
        elif instr.opcode == 'stloc':
            local_index = instr.operand
        else:
            return
        
        if local_index < len(self.locals):
            local_name = self.locals[local_index].get('name', f'local{local_index}')
            local_type = self.locals[local_index].get('type', 'var')
            self.output.append(f"    {local_type} {local_name} = /* stack */;")
        else:
            self.output.append(f"    // stloc local[{local_index}]")
    
    def _load_constant(self, instr: ILInstruction) -> None:
        """Handle ldc* instructions."""
        if instr.opcode == 'ldc.i4.m1':
            value = -1
        elif instr.opcode == 'ldc.i4.0':
            value = 0
        elif instr.opcode == 'ldc.i4.1':
            value = 1
        elif instr.opcode == 'ldc.i4.2':
            value = 2
        elif instr.opcode == 'ldc.i4.3':
            value = 3
        elif instr.opcode == 'ldc.i4.4':
            value = 4
        elif instr.opcode == 'ldc.i4.5':
            value = 5
        elif instr.opcode == 'ldc.i4.6':
            value = 6
        elif instr.opcode == 'ldc.i4.7':
            value = 7
        elif instr.opcode == 'ldc.i4.8':
            value = 8
        elif instr.opcode == 'ldc.i4.s':
            value = instr.operand
        elif instr.opcode == 'ldc.i4':
            value = instr.operand
        elif instr.opcode == 'ldc.i8':
            value = instr.operand
        elif instr.opcode == 'ldc.r4':
            value = instr.operand
        elif instr.opcode == 'ldc.r8':
            value = instr.operand
        elif instr.opcode == 'ldnull':
            value = 'null'
        else:
            return
        
        if isinstance(value, str):
            self.output.append(f"    // push {value}")
        elif isinstance(value, float):
            self.output.append(f"    // push {value}f")
        else:
            self.output.append(f"    // push {value}")
    
    def _call_method(self, instr: ILInstruction) -> None:
        """Handle call/callvirt instructions."""
        if isinstance(instr.operand, str):
            method_name = instr.operand
            # Simple method call
            self.output.append(f"    {method_name}();")
        else:
            self.output.append(f"    // call {instr.operand}")
    
    def _new_object(self, instr: ILInstruction) -> None:
        """Handle newobj instruction."""
        if isinstance(instr.operand, str):
            type_name = instr.operand
            self.output.append(f"    new {type_name}()")
        else:
            self.output.append(f"    // newobj {instr.operand}")
    
    def _load_field(self, instr: ILInstruction) -> None:
        """Handle ldfld/ldsfld instructions."""
        if isinstance(instr.operand, str):
            field_name = instr.operand
            if instr.opcode == 'ldfld':
                self.output.append(f"    // this.{field_name}")
            else:
                self.output.append(f"    // {field_name}")
        else:
            self.output.append(f"    // ldfld {instr.operand}")
    
    def _store_field(self, instr: ILInstruction) -> None:
        """Handle stfld/stsfld instructions."""
        if isinstance(instr.operand, str):
            field_name = instr.operand
            if instr.opcode == 'stfld':
                self.output.append(f"    // this.{field_name} = /* stack */")
            else:
                self.output.append(f"    // {field_name} = /* stack */")
        else:
            self.output.append(f"    // stfld {instr.operand}")
    
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
        
        operator = op_map.get(instr.opcode, instr.opcode)
        self.output.append(f"    // binary op: {operator}")
    
    def _unary_operation(self, instr: ILInstruction, op: str) -> None:
        """Handle unary operations."""
        self.output.append(f"    // unary op: {op}")
    
    def _comparison(self, instr: ILInstruction) -> None:
        """Handle comparison operations."""
        op_map = {
            'ceq': '==',
            'cgt': '>',
            'clt': '<',
            'cgt.un': '>',
            'clt.un': '<',
        }
        
        operator = op_map.get(instr.opcode, instr.opcode)
        self.output.append(f"    // comparison: {operator}")
    
    def _branch(self, instr: ILInstruction) -> None:
        """Handle branch instructions."""
        op_map = {
            'br': 'goto',
            'brtrue': 'if (/* condition */) goto',
            'brfalse': 'if (!/* condition */) goto',
            'beq': 'if (/* a == b */) goto',
            'bge': 'if (/* a >= b */) goto',
            'bgt': 'if (/* a > b */) goto',
            'ble': 'if (/* a <= b */) goto',
            'blt': 'if (/* a < b */) goto',
            'bne.un': 'if (/* a != b */) goto',
            'bge.un': 'if (/* (uint)a >= (uint)b */) goto',
            'bgt.un': 'if (/* (uint)a > (uint)b */) goto',
            'ble.un': 'if (/* (uint)a <= (uint)b */) goto',
            'blt.un': 'if (/* (uint)a < (uint)b */) goto',
        }
        
        if instr.opcode in op_map:
            op = op_map[instr.opcode]
            if isinstance(instr.operand, int):
                target_offset = instr.offset + instr.operand
                label_name = self._get_label_name(target_offset)
                self.output.append(f"    {op} {label_name};")
            else:
                self.output.append(f"    {op} /* target */;")
    
    def _is_inst(self, instr: ILInstruction) -> None:
        """Handle isinst instruction."""
        if isinstance(instr.operand, str):
            type_name = instr.operand
            self.output.append(f"    // isinst {type_name}")
        else:
            self.output.append(f"    // isinst {instr.operand}")
    
    def _new_array(self, instr: ILInstruction) -> None:
        """Handle newarr instruction."""
        if isinstance(instr.operand, str):
            type_name = instr.operand
            self.output.append(f"    new {type_name}[/* size */]")
        else:
            self.output.append(f"    // newarr {instr.operand}")
    
    def _load_length(self, instr: ILInstruction) -> None:
        """Handle ldlen instruction."""
        self.output.append("    // array.Length")
    
    def _load_element(self, instr: ILInstruction) -> None:
        """Handle ldelem* instructions."""
        if instr.opcode == 'ldelem.any':
            self.output.append("    // array[index]")
        else:
            self.output.append(f"    // {instr.opcode}")
    
    def _store_element(self, instr: ILInstruction) -> None:
        """Handle stelem* instructions."""
        self.output.append(f"    // {instr.opcode}")
    
    def _get_label_name(self, offset: int) -> str:
        """Get or create a label name for an offset."""
        if offset not in self.labels:
            self.labels[offset] = f"IL_{offset:04X}"
        return self.labels[offset]
