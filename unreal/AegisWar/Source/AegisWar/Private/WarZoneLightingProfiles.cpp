#include "WarZoneLightingSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
    FWarZoneLightingProfile Profile(const TCHAR* Zone, const TCHAR* Theme, float Sun, float Fill, float Pitch, float Yaw,
        const TCHAR* Warm, const TCHAR* Cool, float Density, const TCHAR* Haze, float Start, float Exposure, float Saturation, float Gamma,
        bool bAuthored = false)
    {
        return { FName(Zone), Theme, FRotator(Pitch,Yaw,0), FLinearColor(FColor::FromHex(Warm)),
            FLinearColor(FColor::FromHex(Cool)), FLinearColor(FColor::FromHex(Haze)),
            Sun, Fill, Density, Start, Exposure, Saturation, Gamma, bAuthored };
    }
}

const TArray<FWarZoneLightingProfile>& UWarZoneLightingSubsystem::Profiles()
{
    // Art direction follows the existing campaign. Lux, haze and grading are distinct
    // for every zone; lairs retain readable fill until authored interior lights arrive.
    static const TArray<FWarZoneLightingProfile> Values = {
        Profile(TEXT("sunmeadow_march"),TEXT("Warm limestone farmland"),24000,6500,-38,-35,TEXT("FFE5B6"),TEXT("CCDDED"),.0035f,TEXT("CCD5BF"),12000,0,.92f,1.08f),
        Profile(TEXT("cinderfen_outskirts"),TEXT("Amber geothermal marsh"),12500,6500,-24,52,TEXT("FFD397"),TEXT("B5D1C8"),.012f,TEXT("A5A88A"),6500,.6f,.88f,1.16f),
        Profile(TEXT("wardens_hollow"),TEXT("Green woodland shafts"),10500,5000,-57,-20,TEXT("DEEFC4"),TEXT("A8CCC3"),.013f,TEXT("8DA798"),4500,.4f,.85f,1.12f),
        Profile(TEXT("cindermaw_pit"),TEXT("Ember-lit mineral hollow"),8500,5000,-68,100,TEXT("FFC087"),TEXT("A5BBCC"),.016f,TEXT("A38B7C"),3500,.6f,.9f,1.15f),
        Profile(TEXT("brightfen_approach"),TEXT("Soft reed-village morning"),21000,7500,-32,120,TEXT("FFF1CD"),TEXT("BDDAD4"),.009f,TEXT("B4C7B6"),9000,.1f,.94f,1.08f),
        Profile(TEXT("ashen_steppe"),TEXT("Dry ochre high sun"),34000,6500,-62,16,TEXT("FFE0AA"),TEXT("D2DEED"),.004f,TEXT("D4BC96"),16000,-.15f,.88f,1.04f),
        Profile(TEXT("mireglass_den"),TEXT("Cool jade reflections"),9000,6000,-44,95,TEXT("CDE8D8"),TEXT("A9D8DB"),.014f,TEXT("85B7AD"),4000,.45f,.85f,1.14f),
        Profile(TEXT("ashfang_pit"),TEXT("Copper dust and cold stone"),11000,4800,-53,35,TEXT("FFD5A6"),TEXT("B8C8DB"),.011f,TEXT("AD9580"),5000,.3f,.84f,1.1f),
        Profile(TEXT("greybrook_crossing"),TEXT("Silver overcast river market"),16500,10500,-36,-110,TEXT("E4ECF2"),TEXT("BDCFD5"),.008f,TEXT("AFBEC1"),10500,.15f,.82f,1.1f),
        Profile(TEXT("bleakroot_causeway"),TEXT("Drowned olive woodland"),11000,7500,-25,164,TEXT("DDE3BD"),TEXT("A8C4C0"),.017f,TEXT("8F9F8F"),6500,.45f,.74f,1.16f),
        Profile(TEXT("briarwatch_den"),TEXT("Dappled amber briars"),13000,5200,-49,-64,TEXT("F5D4A0"),TEXT("B4CFC2"),.01f,TEXT("A3AA90"),4200,.2f,.9f,1.12f),
        Profile(TEXT("rotwreath_nest"),TEXT("Sallow mist and blue shade"),8000,6500,-66,130,TEXT("D9DEA5"),TEXT("ABC6CE"),.02f,TEXT("939D80"),3000,.65f,.76f,1.18f),
        Profile(TEXT("glassriver_ford"),TEXT("Clear cyan gorge daylight"),42000,9000,-51,22,TEXT("F0F7FF"),TEXT("BFDEEE"),.0025f,TEXT("BAD3DF"),18000,-.2f,.97f,1.04f),
        Profile(TEXT("gorepine_pass"),TEXT("Blue snow with low winter sun"),29000,11500,-32,142,TEXT("E7F0FF"),TEXT("BCD0E8"),.007f,TEXT("B9C9D9"),11500,-.15f,.8f,1.08f),
        Profile(TEXT("glassriver_depths"),TEXT("Aquamarine reflected shafts"),11000,6500,-72,14,TEXT("BFE8EF"),TEXT("ADD1DE"),.012f,TEXT("86ADB9"),3500,.45f,.9f,1.14f),
        Profile(TEXT("gorepine_warrens"),TEXT("Cold entrances and timber warmth"),9500,5700,-55,168,TEXT("E6D3B9"),TEXT("A8C1DF"),.013f,TEXT("929FAC"),4000,.5f,.8f,1.16f),
        Profile(TEXT("ironwood_redoubt"),TEXT("Old-growth filtered gold"),18000,7000,-29,-75,TEXT("F2DEB2"),TEXT("ADCDBA"),.01f,TEXT("9DAF9B"),8500,.25f,.86f,1.12f),
        Profile(TEXT("vilemere_heights"),TEXT("Slate moor under violet cloud"),16000,10000,-44,67,TEXT("E1DFED"),TEXT("BEC8D9"),.011f,TEXT("A6A4B5"),10500,.25f,.76f,1.12f),
        Profile(TEXT("stormbarrow_lair"),TEXT("Storm silver and weathered bronze"),14000,8000,-61,-92,TEXT("D2DFEE"),TEXT("B8C1D6"),.014f,TEXT("929BAD"),4500,.35f,.78f,1.14f),
        Profile(TEXT("nightglass_hollow"),TEXT("Indigo glass with pale openings"),8000,6500,-46,78,TEXT("D4CDF1"),TEXT("AEBFDA"),.015f,TEXT("9892B4"),3800,.6f,.82f,1.18f),
        Profile(TEXT("highvale_rampart"),TEXT("Bright alpine mining terraces"),48000,10500,-57,105,TEXT("F4F7FF"),TEXT("C9DBF0"),.003f,TEXT("CBD9E5"),21000,-.35f,.85f,1.04f),
        Profile(TEXT("obsidian_scar"),TEXT("Copper forge light on basalt"),13500,7500,-20,-140,TEXT("FFC49A"),TEXT("A8BBCD"),.01f,TEXT("AA8E84"),9000,.5f,.86f,1.14f),
        Profile(TEXT("highvale_sanctum"),TEXT("Pearl light and blue crystal"),19000,8000,-73,118,TEXT("EFF0FF"),TEXT("BDD2EB"),.008f,TEXT("B7BED6"),6000,.1f,.86f,1.1f),
        Profile(TEXT("obsidian_maw"),TEXT("Deep amber volcanic glow"),9000,6500,-64,-125,TEXT("FFB789"),TEXT("A4B4D3"),.017f,TEXT("A78077"),3500,.7f,.9f,1.18f),
        Profile(TEXT("aegis_crownworks"),TEXT("Golden workshops and pale stone"),30000,8000,-47,-5,TEXT("FFE3B5"),TEXT("C7D6DD"),.005f,TEXT("C3BDA7"),14000,0,.9f,1.06f),
        Profile(TEXT("rift_crownworks"),TEXT("Mineral violet and furnace haze"),14500,8000,-28,30,TEXT("F4CCB8"),TEXT("B2B9D7"),.013f,TEXT("A69AAF"),8000,.4f,.83f,1.14f),
        Profile(TEXT("dawnline_expanse"),TEXT("Low dawn across broken farmland"),26000,8500,-18,-55,TEXT("FFD4A5"),TEXT("C4D3E7"),.006f,TEXT("C3AF97"),16000,.05f,.86f,1.08f),
        Profile(TEXT("shatterline_expanse"),TEXT("Ashen storm breaks on escarpments"),21000,10000,-41,125,TEXT("E1DFDA"),TEXT("B5C4D8"),.009f,TEXT("ACAEB4"),13000,.15f,.74f,1.1f),
        Profile(TEXT("aegis_gate_fortress"),TEXT("Silver mountain saddle"),38000,11500,-34,70,TEXT("EAF1FF"),TEXT("C2D5EB"),.005f,TEXT("BBCAD9"),17000,-.2f,.85f,1.06f),
        Profile(TEXT("rift_gate_fortress"),TEXT("Violet cliffs and copper gate light"),12500,7800,-16,-90,TEXT("FFD1A7"),TEXT("B9B4DB"),.014f,TEXT("AB8F9E"),10000,.5f,.84f,1.16f),
        Profile(TEXT("aegis_capital"),TEXT("Preserved authored Bastion lighting"),18000,9000,-38,-35,TEXT("DFE9FF"),TEXT("C9D9F4"),.005f,TEXT("616B79"),3500,0,.65f,1,true),
        Profile(TEXT("riftspire_capital"),TEXT("Warm civic braziers in blue mineral dusk"),15500,9000,-29,148,TEXT("FFD7B0"),TEXT("B7CCE1"),.008f,TEXT("A79BAA"),9000,.35f,.82f,1.12f),
    };
    return Values;
}

const FWarZoneLightingProfile* UWarZoneLightingSubsystem::FindProfile(FName Zone)
{ return Profiles().FindByPredicate([Zone](const auto& Profile) { return Profile.Zone == Zone; }); }

FString UWarZoneLightingSubsystem::DescribeProfiles()
{
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (const auto& P : Profiles())
    {
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("zone"),P.Zone.ToString()); Row->SetStringField(TEXT("theme"),P.Theme);
        Row->SetNumberField(TEXT("sunLux"),P.SunLux); Row->SetNumberField(TEXT("fillLux"),P.FillLux);
        Row->SetStringField(TEXT("sunColor"),P.SunColor.ToFColor(true).ToHex()); Row->SetStringField(TEXT("fillColor"),P.FillColor.ToFColor(true).ToHex());
        Row->SetStringField(TEXT("fogColor"),P.FogColor.ToFColor(true).ToHex()); Row->SetNumberField(TEXT("fogDensity"),P.FogDensity);
        Row->SetNumberField(TEXT("sunPitch"),P.SunRotation.Pitch); Row->SetNumberField(TEXT("sunYaw"),P.SunRotation.Yaw);
        Row->SetNumberField(TEXT("fogStartCm"),P.FogStartCm); Row->SetNumberField(TEXT("exposureBias"),P.ExposureBias);
        Row->SetNumberField(TEXT("saturation"),P.Saturation); Row->SetNumberField(TEXT("shadowGamma"),P.ShadowGamma);
        Row->SetBoolField(TEXT("preservesAuthoredLighting"),P.bAuthoredCapital); Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    auto Root = MakeShared<FJsonObject>(); Root->SetArrayField(TEXT("profiles"),Rows); Root->SetBoolField(TEXT("visualApproved"),false);
    FString Result; FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Result)); return Result;
}
