#!/usr/bin/env bash
# RamBaan – human-friendly ZIP / RAR cracker
# Everything is stored under ~/ramBaan
set -euo pipefail

############## CONFIG ##############
JOHN_REPO="https://github.com/openwall/john"
ROCKYOU_URL="https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt"
BASE_DIR="$HOME/ramBaan"
WORDLIST="$BASE_DIR/rockyou.txt"
######################################

############## COLOURS ##############
if [[ -t 1 ]]; then
  RED=$'\e[1;31m'; GREEN=$'\e[1;32m'; YELLOW=$'\e[1;33m'
  BLUE=$'\e[1;34m'; CYAN=$'\e[1;36m'; NC=$'\e[0m'
else RED=; GREEN=; YELLOW=; BLUE=; CYAN=; NC=; fi
######################################

############## UTILS ##############
die()  { printf "${RED}[✗] %s${NC}\n" "$*" >&2; exit 1; }
info() { printf "${BLUE}[*] %s${NC}\n" "$*"; }
ok()   { printf "${GREEN}[✓] %s${NC}\n" "$*"; }
warn() { printf "${YELLOW}[!] %s${NC}\n" "$*"; }

############## TOOLING ##############
install_tools(){
  if ! command -v john &>/dev/null || ! command -v zip2john &>/dev/null || ! command -v rar2john &>/dev/null; then
    warn "Installing john (jumbo) …"
    sudo apt-get -qq update
    sudo apt-get -y install git build-essential libssl-dev zlib1g-dev libgmp-dev &>/dev/null
    tmp=$(mktemp -d)
    git clone --depth 1 "$JOHN_REPO" "$tmp" 2>/dev/null
    ( cd "$tmp/src"; ./configure --disable-openmp && make -sj"$(nproc)" ) >&2
    sudo cp -f "$tmp/run"/{john,zip2john,rar2john} /usr/local/bin/ 2>/dev/null || true
    rm -rf "$tmp"
  fi
  for x in unzip unrar; do command -v "$x" &>/dev/null || sudo apt-get -y install "$x" >&2; done
  ok "Tools ready"
}

############## ROCKYOU ##############
get_rockyou(){
  [[ -s $WORDLIST ]] && return
  info "Downloading rockyou.txt …"
  mkdir -p "$BASE_DIR"
  wget -q "$ROCKYOU_URL" -O "$WORDLIST"
  [[ -s $WORDLIST ]] || die "rockyou.txt download failed"
}

############## HASH ##############
extract_hash(){
  local arch=$1
  [[ -f $arch ]] || die "Archive not found: $arch"
  case "$arch" in
    *.zip) zip2john "$arch" 2>/dev/null > "$hashfile" ;;
    *.rar) rar2john "$arch" 2>/dev/null > "$hashfile" ;;
    *) die "Only .zip / .rar supported" ;;
  esac
  [[ -s $hashfile ]] || die "Could not extract hash – archive corrupt or not password-protected?"
  ok "Hash → $hashfile"
}

############## MASK BUILDER ##############
# turns "uppercase(a-e) lowercase number" into john mask + custom sets
build_mask(){
  local john_mask="" custom_sets="" idx=1
  for piece; do
    case "$piece" in
      "uppercase("*")")
        range=${piece#uppercase(}; range=${range%)}
        range=${range:-A-Z}
        custom_sets+="[${range}]"; john_mask+="?$idx"; ((idx++)) ;;
      "lowercase("*")")
        range=${piece#lowercase(}; range=${range%)}
        range=${range:-a-z}
        custom_sets+="[${range}]"; john_mask+="?$idx"; ((idx++)) ;;
      "number("*")")
        range=${piece#number(}; range=${range%)}
        range=${range:-0-9}
        custom_sets+="[${range}]"; john_mask+="?$idx"; ((idx++)) ;;
      "specialCharacter("*")")
        range=${piece#specialCharacter(}; range=${range%)}
        range=${range:-!@#$%^&*()}
        custom_sets+="[${range}]"; john_mask+="?$idx"; ((idx++)) ;;
      *) die "Bad mask piece: $piece" ;;
    esac
  done
  printf '%s %s' "$john_mask" "$custom_sets"
}

############## ATTACKS ##############
dict_attack(){
  local wl=$1
  [[ $wl == rockyou ]] && { get_rockyou; wl=$WORDLIST; }
  [[ $wl == -listBrute* ]] && wl=$(echo "$wl" | cut -d' ' -f2)
  [[ -f $wl ]] || die "Word-list not found: $wl"
  info "Dictionary attack …"
  john --wordlist="$wl" "$hashfile"
  show_cracked
}

mask_attack(){
  if [[ $# -eq 0 ]]; then
    info "No mask provided, using default (?a?a?a?a)"
    john --mask=?a?a?a?a "$hashfile"
  else
    read -r john_mask custom_sets <<< "$(build_mask "$@")"
    info "Mask attack → $john_mask (sets: $custom_sets)"
    john --mask="$john_mask" --custom-mask="$custom_sets" "$hashfile"
  fi
  show_cracked
}

incr_attack(){
  local mode=$1 len=$2
  case $mode in
    Digits|Alpha|Alnum|All) ;;
    *) die "Invalid charset: $mode (use Digits, Alpha, Alnum, All)" ;;
  esac
  [[ $len =~ ^[0-9]+$ ]] || die "Invalid max-length: $len"
  info "Incremental $mode max-len $len …"
  john --incremental="$mode" --max-length="$len" "$hashfile"
  show_cracked
}

show_cracked(){
  local pass
  pass=$(john --show "$hashfile" | grep -v "0 password hashes" | grep -oP ":.+\$" | cut -d':' -f2 | cut -d'$' -f1)
  if [[ -n $pass ]]; then
    ok "Password cracked: $pass"
    extract_archive "$pass"
  else
    warn "No password cracked yet"
  fi
}

############## EXTRACTION ##############
extract_archive(){
  local pass=$1 dest="$BASE_DIR/extracted_$(basename "$archive" | tr -c 'A-Za-z0-9._-' '_')"
  mkdir -p "$dest"
  case "$archive" in
    *.zip) unzip -q -P "$pass" -d "$dest" "$archive" ;;
    *.rar) unrar x -y -p"$pass" "$archive" "$dest" >/dev/null ;;
  esac
  ok "Archive extracted → $dest"
}

############## HELP ##############
usage(){
  cat <<EOF
RamBaan – human-friendly ZIP/RAR cracker (everything stored in ~/ramBaan)

USAGE
  ramBaan <archive> <MODE> [OPTIONS]

MODES
  --dict [wordlist|rockyou|-listBrute /path/to/wordlist]  Dictionary attack
  --mask <mask-parts>           Mask attack using plain English:
                                  uppercase or uppercase(A-E)
                                  lowercase or lowercase(a-z)
                                  number or number(0-5)
                                  specialCharacter or specialCharacter(!@#)
  --incr <set> <max-len>        Brute-force (set=Digits|Alpha|Alnum|All)
  --show                        Show cracked passwords
  --extract <password>          Extract archive to ~/ramBaan/extracted_*

EXAMPLES
  ramBaan secret.zip --dict rockyou
  ramBaan file.rar --dict -listBrute /path/to/wordlist.txt
  ramBaan file.zip --mask uppercase lowercase number
  ramBaan zipfile --mask uppercase(A-E) number(0-3) specialCharacter
  ramBaan stuff.rar --incr Digits 6
  ramBaan file.zip --show
  ramBaan file.zip --extract MyP@ss

EOF
  exit 0
}

############## CLI ##############
[[ $# -lt 2 ]] && usage
archive=$1; shift
mode=$1; shift

mkdir -p "$BASE_DIR"
hashfile="$BASE_DIR/$(basename "$archive" | tr -c 'A-Za-z0-9._-' '_').hash"
install_tools
extract_hash "$archive"

case "$mode" in
  --dict) dict_attack "${1:-rockyou}" ;;
  --mask) mask_attack "$@" ;;
  --incr|--incrementas) charset=${1:-Alnum}; len=${2:-8}; incr_attack "$charset" "$len" ;;
  --show) show_cracked ;;
  --extract) [[ -z ${1:-} ]] && die "Give password for extraction"; extract_archive "$1" ;;
  --help) usage ;;
  *) die "Unknown mode $mode – try --help" ;;
esac
ok "RamBaan finished – check ~/ramBaan"
################################### EOF #####################################