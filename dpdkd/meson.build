project(
  'pktlab-dpdkd',
  'c',
  version: '0.1.0',
  default_options: [
    'c_std=c11',
    'warning_level=3',
  ],
)

add_project_arguments('-D_POSIX_C_SOURCE=200809L', language: 'c')

pktlab_dpdkd_includes = include_directories('include')
pktlab_dpdkd_src_includes = include_directories('src')

python3 = import('python').find_installation('python3')

pktlab_dpdkd_sources = files(
  'src/main.c',
  'src/daemon.c',
  'src/ipc_server.c',
  'src/json_proto.c',
  'src/health.c',
  'src/stats.c',
  'src/log.c',
)

pktlab_dpdkd = executable(
  'pktlab-dpdkd',
  pktlab_dpdkd_sources,
  include_directories: [pktlab_dpdkd_includes, pktlab_dpdkd_src_includes],
)

test(
  'ipc-smoke',
  python3,
  args: [
    meson.current_source_dir() / 'tests' / 'integration' / 'test_ipc_smoke.py',
    pktlab_dpdkd.full_path(),
  ],
)
