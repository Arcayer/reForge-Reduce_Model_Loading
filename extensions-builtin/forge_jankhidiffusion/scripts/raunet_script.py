import sys
import os

# Add the parent directory of the extension to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
extension_dir = os.path.dirname(script_dir)
sys.path.insert(0, os.path.dirname(extension_dir))

print(f"Extension directory added to sys.path: {os.path.dirname(extension_dir)}")

import gradio as gr
from modules import scripts

# Now import from your package
from forge_jankhidiffusion.raunet import ApplyRAUNet, ApplyRAUNetSimple, UPSCALE_METHODS
from forge_jankhidiffusion.msw_msa_attention import ApplyMSWMSAAttention, ApplyMSWMSAAttentionSimple

print("Imports successful in RAUNet script")
opApplyRAUNet = ApplyRAUNet()
opApplyMSWMSA = ApplyMSWMSAAttention()

class RAUNetScript(scripts.Script):
    sorting_priority = 15  # Adjust this as needed

    def title(self):
        return "RAUNet and MSW-MSA for Forge"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, *args, **kwargs):
        with gr.Accordion(open=False, label=self.title()):
            with gr.Tab("RAUNet"):
                raunet_enabled = gr.Checkbox(label="RAUNet Enabled", value=False)
                
                with gr.Group(visible=False) as raunet_options:
                    raunet_model_type = gr.Radio(choices=["SD 1.5", "SDXL"], value="SD 1.5", label="Model Type")
                    input_blocks = gr.Text(label="Input Blocks", value="3")
                    output_blocks = gr.Text(label="Output Blocks", value="8")
                    time_mode = gr.Dropdown(choices=["percent", "timestep", "sigma"], value="percent", label="Time Mode")
                    start_time = gr.Slider(label="Start Time", minimum=0.0, maximum=1.0, step=0.01, value=0.0)
                    end_time = gr.Slider(label="End Time", minimum=0.0, maximum=1.0, step=0.01, value=0.45)
                    two_stage_upscale = gr.Checkbox(label="Two Stage Upscale", value=False)
                    upscale_mode = gr.Dropdown(choices=UPSCALE_METHODS, value="bicubic", label="Upscale Mode")
            
                    with gr.Accordion(open=False, label="Cross-Attention Settings"):
                        ca_start_time = gr.Slider(label="CA Start Time", minimum=0.0, maximum=1.0, step=0.01, value=0.0)
                        ca_end_time = gr.Slider(label="CA End Time", minimum=0.0, maximum=1.0, step=0.01, value=0.3)
                        ca_input_blocks = gr.Text(label="CA Input Blocks", value="4")
                        ca_output_blocks = gr.Text(label="CA Output Blocks", value="8")
                        ca_upscale_mode = gr.Dropdown(choices=UPSCALE_METHODS, value="bicubic", label="CA Upscale Mode")

                    gr.Markdown("""
                    ### Notes for RAUNet:
                    - Helps avoid artifacts when generating at resolutions significantly higher than what the model normally supports.
                    - Not beneficial (and may harm quality) when generating at low resolutions.
                    - For SD 1.5: Recommended settings are input 3, output 8, CA input 4, CA output 8, start 0.0, end 0.45, CA start 0.0, CA end 0.3.
                    - For SDXL: Try input 3, output 5 and disable CA (set ca_start_time to 1.0), or set CA input 2, CA output 7 and disable upsampler/downsampler patch (set start_time to 1.0).
                    - Don't enable both CA and upsampler/downsampler patches for SDXL at the same time.
                    """)

            with gr.Tab("MSW-MSA"):
                mswmsa_enabled = gr.Checkbox(label="MSW-MSA Enabled", value=False)
                
                with gr.Group(visible=False) as mswmsa_options:
                    mswmsa_model_type = gr.Radio(choices=["SD 1.5", "SDXL"], value="SD 1.5", label="Model Type")
                    mswmsa_input_blocks = gr.Text(label="Input Blocks", value="1,2")
                    mswmsa_middle_blocks = gr.Text(label="Middle Blocks", value="")
                    mswmsa_output_blocks = gr.Text(label="Output Blocks", value="9,10,11")
                    mswmsa_time_mode = gr.Dropdown(choices=["percent", "timestep", "sigma"], value="percent", label="Time Mode")
                    mswmsa_start_time = gr.Slider(label="Start Time", minimum=0.0, maximum=1.0, step=0.01, value=0.0)
                    mswmsa_end_time = gr.Slider(label="End Time", minimum=0.0, maximum=1.0, step=0.01, value=1.0)

                    gr.Markdown("""
                    ### Notes for MSW-MSA:
                    - Most effective at higher resolutions (1536+ for SD 1.5, 2048+ for SDXL).
                    - For extreme resolutions (over 2048), try starting at 0.2 or after other scaling effects end.
                    - Use image sizes that are multiples of 32, 64, or 128 to avoid tensor size mismatch errors.
                    - Not compatible with HyperTile, Deep Cache, Nearsighted/Slothful attention, or other attention patches affecting the same blocks.
                    """)

            gr.HTML("<p><i>Note: MSW-MSA seems to not be working at the moment.</i></p>")

        # Add JavaScript to handle visibility and model-specific settings
        raunet_enabled.change(
            fn=lambda x: gr.Group.update(visible=x),
            inputs=[raunet_enabled],
            outputs=[raunet_options]
        )

        mswmsa_enabled.change(
            fn=lambda x: gr.Group.update(visible=x),
            inputs=[mswmsa_enabled],
            outputs=[mswmsa_options]
        )

        def update_raunet_settings(model_type):
            if model_type == "SD 1.5":
                return "3", "8", "4", "8", 0.0, 0.45, 0.0, 0.3
            else:  # SDXL
                return "3", "5", "2", "7", 1.0, 1.0, 1.0, 1.0  # Disabling both patches by default for SDXL

        raunet_model_type.change(
            fn=update_raunet_settings,
            inputs=[raunet_model_type],
            outputs=[input_blocks, output_blocks, ca_input_blocks, ca_output_blocks, start_time, end_time, ca_start_time, ca_end_time]
        )

        def update_mswmsa_settings(model_type):
            if model_type == "SD 1.5":
                return "1,2", "", "9,10,11"
            else:  # SDXL
                return "4,5", "", "4,5"

        mswmsa_model_type.change(
            fn=update_mswmsa_settings,
            inputs=[mswmsa_model_type],
            outputs=[mswmsa_input_blocks, mswmsa_middle_blocks, mswmsa_output_blocks]
        )

        return (raunet_enabled, raunet_model_type, input_blocks, output_blocks, time_mode, start_time, end_time, 
                two_stage_upscale, upscale_mode, ca_start_time, ca_end_time, ca_input_blocks, ca_output_blocks, ca_upscale_mode,
                mswmsa_enabled, mswmsa_model_type, mswmsa_input_blocks, mswmsa_middle_blocks, mswmsa_output_blocks, 
                mswmsa_time_mode, mswmsa_start_time, mswmsa_end_time)

    def process_before_every_sampling(self, p, *script_args, **kwargs):
        (
            raunet_enabled, raunet_model_type, input_blocks, output_blocks, time_mode, start_time, end_time, 
            two_stage_upscale, upscale_mode, ca_start_time, ca_end_time, ca_input_blocks, ca_output_blocks, ca_upscale_mode,
            mswmsa_enabled, mswmsa_model_type, mswmsa_input_blocks, mswmsa_middle_blocks, mswmsa_output_blocks, 
            mswmsa_time_mode, mswmsa_start_time, mswmsa_end_time
        ) = script_args

        # Always start with a fresh clone of the original unet
        unet = p.sd_model.forge_objects.unet.clone()

        if raunet_enabled:
            unet = opApplyRAUNet.patch(
                True, unet, input_blocks, output_blocks, time_mode, start_time, end_time, two_stage_upscale, upscale_mode,
                ca_start_time, ca_end_time, ca_input_blocks, ca_output_blocks, ca_upscale_mode
            )[0]
            p.extra_generation_params.update(
                dict(
                    raunet_enabled=raunet_enabled,
                    raunet_model_type=raunet_model_type,
                    raunet_input_blocks=input_blocks,
                    raunet_output_blocks=output_blocks,
                    raunet_time_mode=time_mode,
                    raunet_start_time=start_time,
                    raunet_end_time=end_time,
                    raunet_two_stage_upscale=two_stage_upscale,
                    raunet_upscale_mode=upscale_mode,
                    raunet_ca_start_time=ca_start_time,
                    raunet_ca_end_time=ca_end_time,
                    raunet_ca_input_blocks=ca_input_blocks,
                    raunet_ca_output_blocks=ca_output_blocks,
                    raunet_ca_upscale_mode=ca_upscale_mode,
                )
            )
        else:
            # Apply RAUNet patch with enabled=False to reset any modifications
            unet = opApplyRAUNet.patch(False, unet, "", "", "", 0, 0, False, "", 0, 0, "", "", "")[0]
            p.extra_generation_params.update(dict(raunet_enabled=False))

        if mswmsa_enabled:
            unet = opApplyMSWMSA.patch(
                unet, mswmsa_input_blocks, mswmsa_middle_blocks, mswmsa_output_blocks, mswmsa_time_mode, mswmsa_start_time, mswmsa_end_time
            )[0]
            p.extra_generation_params.update(
                dict(
                    mswmsa_enabled=mswmsa_enabled,
                    mswmsa_model_type=mswmsa_model_type,
                    mswmsa_input_blocks=mswmsa_input_blocks,
                    mswmsa_middle_blocks=mswmsa_middle_blocks,
                    mswmsa_output_blocks=mswmsa_output_blocks,
                    mswmsa_time_mode=mswmsa_time_mode,
                    mswmsa_start_time=mswmsa_start_time,
                    mswmsa_end_time=mswmsa_end_time,
                )
            )
        else:
            # Apply MSW-MSA patch with empty block settings to reset any modifications
            unet = opApplyMSWMSA.patch(unet, "", "", "", mswmsa_time_mode, 0, 0)[0]
            p.extra_generation_params.update(dict(mswmsa_enabled=False))

        # Always update the unet
        p.sd_model.forge_objects.unet = unet

        # Add debug prints to verify the patches are being applied
        print(f"RAUNet enabled: {raunet_enabled}, Model Type: {raunet_model_type}")
        print(f"RAUNet settings: Input Blocks: {input_blocks}, Output Blocks: {output_blocks}, CA Input Blocks: {ca_input_blocks}, CA Output Blocks: {ca_output_blocks}")
        print(f"MSW-MSA enabled: {mswmsa_enabled}, Model Type: {mswmsa_model_type}")
        print(f"MSW-MSA settings: Input Blocks: {mswmsa_input_blocks}, Output Blocks: {mswmsa_output_blocks}")

        return