#include "Misc/AutomationTest.h"
#include "HAL/IConsoleManager.h"
#include "WarCitadelLumenStudyRuntime.h"
#include "WarCitadelLumenViewProbe.h"
#include "Dom/JsonObject.h"
#include "RenderingThread.h"
#include "WarCitadelLightingWitness.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/UnrealType.h"
#include "UObject/Package.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "GameFramework/Actor.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelPrivateMaterialReadbackTest,"AegisWar.Foundation.CitadelPrivateMaterialReadback",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCitadelPrivateMaterialReadbackTest::RunTest(const FString&)
{
    using WarCitadelLightingWitness::PrivateMaterialResourceReady;
    TestTrue(TEXT("Intended ready material is admitted"),PrivateMaterialResourceReady(true,false,true));
    TestFalse(TEXT("A valid WorldGrid fallback cannot admit capture"),PrivateMaterialResourceReady(false,true,true));
    TestFalse(TEXT("Fallback is rejected even with matching ownership"),PrivateMaterialResourceReady(true,true,true));
    TestFalse(TEXT("A different valid interface cannot admit capture"),PrivateMaterialResourceReady(false,false,true));
    TestFalse(TEXT("An unfinished intended shader cannot admit capture"),PrivateMaterialResourceReady(true,false,false));
    for (const TCHAR* Role:{TEXT("rock"),TEXT("dark_seam"),TEXT("snow")})
    {
        const FString Name=FString(TEXT("M_DistantCrag_"))+Role;
        const FString Path=TEXT("/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Materials/")+Name+TEXT(".")+Name;
        TestTrue(TEXT("Fresh private crag material participates in readiness"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(Path));
        TestFalse(TEXT("Mismatched crag object cannot bypass discovery"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(Path+TEXT("_other")));
    }
    TestFalse(TEXT("Crag material outside a private city is excluded"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(
        TEXT("/Game/Materials/M_DistantCrag_rock.M_DistantCrag_rock")));
    TestFalse(TEXT("Unknown crag role is excluded"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(
        TEXT("/Game/WorldRebuild/AegisCitadel_aaaaaaaaaaaa/Materials/M_DistantCrag_lava.M_DistantCrag_lava")));
    TestFalse(TEXT("Malformed revision is excluded"),WarCitadelLightingWitness::PrivateSurfaceMaterialPath(
        TEXT("/Game/WorldRebuild/AegisCitadel_AAAAAAAAAAAA/Materials/M_DistantCrag_snow.M_DistantCrag_snow")));
    TestFalse(TEXT("Absent renderer cannot admit capture"),WarCitadelLightingWitness::PrivateMaterialReadiness(nullptr)->GetBoolField(TEXT("ready")));
    TestTrue(TEXT("Absent component has no invented bindings"),WarCitadelLightingWitness::CapturePrivateSurfaceMaterials(nullptr).IsEmpty());
    auto* Package=CreatePackage(TEXT("/Temp/CitadelMaterialReadback/M_PrivateSurface_Test"));
    auto* Material=NewObject<UMaterial>(Package,TEXT("M_PrivateSurface_Test"));
    auto* Owner=NewObject<AActor>();auto* Component=NewObject<UStaticMeshComponent>(Owner);
    auto* Mesh=NewObject<UStaticMesh>();Mesh->GetStaticMaterials().Add(FStaticMaterial(Material));
    Component->SetStaticMesh(Mesh);Component->SetMaterial(0,Material);
    const auto BeforeMaterials=Component->GetMaterials();const bool bDirty=Package->IsDirty();
    const auto Rows=WarCitadelLightingWitness::CapturePrivateSurfaceMaterials(Component);
    if (!TestEqual(TEXT("Private component binding is present"),Rows.Num(),1)) return false;
    const auto& Row=Rows[0];
    TestEqual(TEXT("Exact component material is read"),Row->GetStringField(TEXT("material")),Material->GetPathName());
    TestEqual(TEXT("Exact material slot is read"),Row->GetIntegerField(TEXT("materialSlot")),0);
    TestFalse(TEXT("No world cannot invent an effective renderer"),Row->GetBoolField(TEXT("rendererAvailable")));
    TestFalse(TEXT("No renderer cannot invent proxy evidence"),Row->GetObjectField(TEXT("renderMaterial"))->GetBoolField(TEXT("available")));
    TestFalse(TEXT("Object readback cannot approve submitted batches"),Row->GetBoolField(TEXT("submittedMeshBatchVerified")));
    TestFalse(TEXT("Object readback cannot approve screenshot pixels"),Row->GetBoolField(TEXT("screenshotPixelBindingVerified")));
    TestFalse(TEXT("Object readback cannot approve appearance"),Row->GetBoolField(TEXT("visualApproved")));
    TestTrue(TEXT("Component materials remain unchanged"),Component->GetMaterials()==BeforeMaterials);
    TestEqual(TEXT("Private material package dirtiness remains unchanged"),Package->IsDirty(),bDirty);
    Component->SetMaterial(0,NewObject<UMaterial>());
    TestTrue(TEXT("Ordinary materials remain outside this diagnostic"),WarCitadelLightingWitness::CapturePrivateSurfaceMaterials(Component).IsEmpty());
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelLightingStudyTest,"AegisWar.Foundation.CitadelLightingStudy",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCitadelLightingStudyTest::RunTest(const FString&)
{
    using namespace WarCitadelLumenStudyRuntime;
    TMap<FString,int32> Values;
    TestTrue(TEXT("software recipe"),Recipe(TEXT("lumen_software"),Values));
    TestEqual(TEXT("software gates"),Values.Num(),8);
    TestEqual(TEXT("software backend"),Values[TEXT("r.Lumen.HardwareRayTracing")],0);
    TestTrue(TEXT("hardware recipe"),Recipe(TEXT("lumen_hardware"),Values));
    TestEqual(TEXT("hardware gates"),Values.Num(),6);
    TestFalse(TEXT("ordinary rendering has no override"),Recipe(TEXT("ordinary"),Values));
    TestTrue(TEXT("invalid recipe clears prior values"),Values.IsEmpty());
    ReviewRecipe(Values);
    TestEqual(TEXT("full-resolution review request"),Values[TEXT("r.ScreenPercentage")],100);
    TestEqual(TEXT("review shadows are requested"),Values[TEXT("r.ShadowQuality")],5);
    TestEqual(TEXT("review controls remain separate from GI backend"),Values.Num(),8);
    TestFalse(TEXT("capture preset does not invent a Lumen backend"),Values.Contains(TEXT("r.Lumen.HardwareRayTracing")));
    for (const auto& Pair:Values)
    {
        const auto* Variable=IConsoleManager::Get().FindConsoleVariable(*Pair.Key);
        TestNotNull(TEXT("Installed renderer exposes each review control: ")+Pair.Key,Variable);
        if (Variable) TestFalse(TEXT("Review control is not a readonly startup gate: ")+Pair.Key,
            (Variable->GetFlags() & ECVF_ReadOnly)!=0);
    }
#if !UE_BUILD_SHIPPING
    auto& Manager=IConsoleManager::Get();
    const FString Name=TEXT("war.Test.CitadelLumenTemporary");
    auto* Variable=Manager.RegisterConsoleVariable(*Name,0,TEXT("Scoped lighting test"));
    Variable->Set(3,ECVF_SetByGameSetting);
    {
        FOverride Override;FString Error;
        TestTrue(TEXT("temporary override applied"),Override.Apply({{Name,1}},Error));
        TestEqual(TEXT("temporary value"),Variable->GetInt(),1);
        Variable->Set(4,ECVF_SetByGameSetting);
    }
    TestEqual(TEXT("latest underlying setting restored"),Variable->GetInt(),4);
    TestEqual(TEXT("underlying priority restored"),Variable->GetFlags() & ECVF_SetByMask,int32(ECVF_SetByGameSetting));
    {
        FOverride Override;FString Error;
        TestFalse(TEXT("missing CVar rejects whole recipe"),Override.Apply({{Name,1},{TEXT("war.Test.AbsentLumenCvar"),1}},Error));
        TestEqual(TEXT("failed recipe leaves settings alone"),Variable->GetInt(),4);
        Variable->Set(7,ECVF_SetByConsole);
        TestFalse(TEXT("console priority preserved"),Override.Apply({{Name,1}},Error));
        TestEqual(TEXT("console value preserved"),Variable->GetInt(),7);
    }
    Manager.UnregisterConsoleObject(*Name,false);
#endif
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelConsoleReadbackTest,"AegisWar.Foundation.CitadelConsoleReadback",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCitadelConsoleReadbackTest::RunTest(const FString&)
{
    int32 Integer=7;float Fractional=83.5f;
    FAutoConsoleVariableRef IntegerRef(TEXT("war.Test.CitadelReadbackInteger"),Integer,TEXT("Readback test"),ECVF_RenderThreadSafe);
    FAutoConsoleVariableRef FloatRef(TEXT("war.Test.CitadelReadbackFloat"),Fractional,TEXT("Readback test"),ECVF_RenderThreadSafe);
    auto& Manager=IConsoleManager::Get();
    auto* Float=Manager.FindConsoleVariable(TEXT("war.Test.CitadelReadbackFloat"));
    Float->Set(87.25f,ECVF_SetByGameSetting);
    double RenderInteger=0,RenderFractional=0;
    bool RenderAvailable=false;
    ENQUEUE_RENDER_COMMAND(CitadelConsoleReadback)([&](FRHICommandListImmediate&)
    {
        const auto A=WarCitadelLumenViewProbe::ReadConsoleVariable(TEXT("war.Test.CitadelReadbackInteger"));
        const auto B=WarCitadelLumenViewProbe::ReadConsoleVariable(TEXT("war.Test.CitadelReadbackFloat"));
        RenderAvailable=A->GetBoolField(TEXT("available")) && B->GetBoolField(TEXT("available"));
        RenderInteger=A->GetNumberField(TEXT("value"));RenderFractional=B->GetNumberField(TEXT("value"));
    });
    FlushRenderingCommands();
    TestTrue(TEXT("reference CVars are readable without typed-data access"),RenderAvailable);
    TestEqual(TEXT("integer reference value"),RenderInteger,7.);
    TestEqual(TEXT("render-side fractional value retains precision"),RenderFractional,87.25);
    const auto Readback=WarCitadelLumenViewProbe::ReadConsoleVariable(TEXT("war.Test.CitadelReadbackFloat"));
    TestEqual(TEXT("priority is read without mutation"),int32(Readback->GetNumberField(TEXT("setByFlags"))),int32(ECVF_SetByGameSetting));
    TestEqual(TEXT("readback leaves backing storage alone"),Fractional,87.25f);
    const auto Missing=WarCitadelLumenViewProbe::ReadConsoleVariable(TEXT("war.Test.AbsentCitadelReadback"));
    TestFalse(TEXT("missing variables stay unavailable"),Missing->GetBoolField(TEXT("available")));
    TestFalse(TEXT("missing values are never invented"),Missing->HasField(TEXT("value")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelBackdropPolicyTest,"AegisWar.Foundation.CitadelBackdropPolicy",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarCitadelBackdropPolicyTest::RunTest(const FString&)
{
    auto* Mesh=NewObject<UStaticMeshComponent>();
    Mesh->SetCollisionProfileName(TEXT("NoCollision"));
    const auto Initial=WarCitadelLightingWitness::CaptureBackdrop(Mesh);
    const auto Properties=Initial->GetObjectField(TEXT("properties"));
    TestEqual(TEXT("every required native boolean is recorded"),Properties->Values.Num(),18);
    TestFalse(TEXT("explicit profile disables default mesh collision"),Properties->GetBoolField(TEXT("use_default_collision")));
    // Start from actual native fields, including inherited bitfield properties.
    for (const auto& Pair:Properties->Values)
        TestFalse(TEXT("required native backdrop property exists"),Pair.Value->IsNull());
    for (TFieldIterator<FBoolProperty> It(Mesh->GetClass());It;++It)
        if (It->GetFName()==TEXT("CastShadow") || It->GetName().StartsWith(TEXT("bCast"))
            || It->GetFName()==TEXT("bSelfShadowOnly") || It->GetFName()==TEXT("bGenerateOverlapEvents")
            || It->GetName().StartsWith(TEXT("bAffect")) || It->GetFName()==TEXT("bVisibleInRayTracing"))
            It->SetPropertyValue_InContainer(Mesh,false);
    Mesh->SetCanEverAffectNavigation(false);
    TestTrue(TEXT("disabled native backdrop controls match"),WarCitadelLightingWitness::CaptureBackdrop(Mesh)->GetBoolField(TEXT("controlsMatch")));
    Mesh->SetGenerateOverlapEvents(true);
    TestFalse(TEXT("enabled overlap is rejected"),WarCitadelLightingWitness::CaptureBackdrop(Mesh)->GetBoolField(TEXT("controlsMatch")));
    Mesh->SetGenerateOverlapEvents(false);Mesh->SetCollisionProfileName(TEXT("BlockAll"));
    TestFalse(TEXT("restored blocking profile is rejected"),WarCitadelLightingWitness::CaptureBackdrop(Mesh)->GetBoolField(TEXT("controlsMatch")));
    return true;
}
#endif
