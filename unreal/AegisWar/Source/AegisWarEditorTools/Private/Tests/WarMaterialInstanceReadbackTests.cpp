#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarImportLibrary.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceConstant.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "EditorFramework/AssetImportData.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"
#include "UObject/UnrealType.h"
#include <limits>

namespace
{
    TSharedPtr<FJsonObject> ReadInstance(UMaterialInstance* Instance)
    {
        TSharedPtr<FJsonObject> Json;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(UWarImportLibrary::DescribeMaterialInstance(Instance)),Json);
        return Json;
    }
    UMaterialInstanceConstant* Fixture()
    {
        auto* Instance=NewObject<UMaterialInstanceConstant>(GetTransientPackage());
        Instance->Parent=NewObject<UMaterial>(GetTransientPackage());
        return Instance;
    }
    const TArray<FString> Flags={TEXT("bOverride_OpacityMaskClipValue"),TEXT("bOverride_BlendMode"),TEXT("bOverride_ShadingModel"),
        TEXT("bOverride_DitheredLODTransition"),TEXT("bOverride_CastDynamicShadowAsMasked"),TEXT("bOverride_TwoSided"),
        TEXT("bOverride_bIsThinSurface"),TEXT("bOverride_OutputTranslucentVelocity"),TEXT("bOverride_bHasPixelAnimation"),
        TEXT("bOverride_bEnableTessellation"),TEXT("bOverride_DisplacementScaling"),TEXT("bOverride_bEnableDisplacementFade"),
        TEXT("bOverride_DisplacementFadeRange"),TEXT("bOverride_MaxWorldPositionOffsetDisplacement"),TEXT("bOverride_CompatibleWithLumenCardSharing")};
    const TArray<FString> BoolValues={TEXT("TwoSided"),TEXT("bIsThinSurface"),TEXT("DitheredLODTransition"),TEXT("bCastDynamicShadowAsMasked"),
        TEXT("bOutputTranslucentVelocity"),TEXT("bHasPixelAnimation"),TEXT("bEnableTessellation"),TEXT("bEnableDisplacementFade"),TEXT("bCompatibleWithLumenCardSharing")};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMaterialInstanceReadback,"AegisWar.Foundation.CitadelMaterialInstanceReadback",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarMaterialInstanceReadback::RunTest(const FString&)
{
    auto* Instance=Fixture();auto& Overrides=Instance->BasePropertyOverrides;
    auto* Type=FMaterialInstanceBasePropertyOverrides::StaticStruct();
    for (const auto& Name:BoolValues)
    {
        auto* Property=FindFProperty<FBoolProperty>(Type,*Name);
        if (!TestNotNull(*Name,Property)) return false;
        Property->SetPropertyValue_InContainer(&Overrides,true);
    }
    Overrides.BlendMode=BLEND_Masked;Overrides.ShadingModel=MSM_DefaultLit;
    Overrides.OpacityMaskClipValue=.625f;Overrides.MaxWorldPositionOffsetDisplacement=127.f;
    Overrides.DisplacementScaling.Magnitude=13.25f;Overrides.DisplacementScaling.Center=-.375f;
    Overrides.DisplacementFadeRange.StartSizePixels=64.f;Overrides.DisplacementFadeRange.EndSizePixels=32.f;
    Overrides.UsageFlags=0xf1234567u;Overrides.bOverride_UsageFlags=0xd2345678u;
    auto& Vector=Instance->VectorParameterValues.Add_GetRef(FVectorParameterValue(FMaterialParameterInfo(TEXT("Base_Color_Tint")),FLinearColor(.37f,.4f,.44f,1.f)));
    Vector.ExpressionGUID=FGuid(1,2,3,4);
    Vector.ParameterName_DEPRECATED=TEXT("LegacyTintEvidence");
    Instance->bOverridePhysMaterial=true;Instance->bOverrideSubsurfaceProfile=true;
    Instance->bOverrideSpecularProfile=true;Instance->bOverrideToonProfile=true;
    Instance->bOverrideBlendableLocation=true;Instance->bOverrideBlendablePriority=true;
    Instance->BlendablePriorityOverride=11;Instance->NaniteOverrideMaterial.bEnableOverride=false;
    Instance->PhysicalMaterialMap[2]=NewObject<UPhysicalMaterial>(GetTransientPackage());
    Instance->UserSceneTextureOverrides.AddDefaulted();
    Instance->EnumerationObjects.Emplace(FSoftObjectPath(TEXT("/Game/Unloaded/Enumeration.Enumeration")));
    const bool WasDirty=Instance->GetPackage()->IsDirty();
    FString Stable;
    for (bool Enabled:{false,true})
    {
        for (const auto& Name:Flags)
        {
            auto* Property=FindFProperty<FBoolProperty>(Type,*Name);
            if (!TestNotNull(*Name,Property)) return false;
            Property->SetPropertyValue_InContainer(&Overrides,Enabled);
        }
        auto Json=ReadInstance(Instance);
        if (!TestTrue(TEXT("Descriptor JSON"),Json.IsValid())) return false;
        TestEqual(TEXT("Exact top-level contract"),Json->Values.Num(),12);
        TestTrue(TEXT("Typed complete readback"),Json->GetBoolField(TEXT("available")));
        TestTrue(TEXT("Read only"),Json->GetBoolField(TEXT("readOnly")));
        TestTrue(TEXT("Complete override inventory"),Json->GetBoolField(TEXT("overrideInventoryComplete")));
        TestTrue(TEXT("Complete settings inventory"),Json->GetBoolField(TEXT("settingsInventoryComplete")));
        const auto Properties=Json->GetObjectField(TEXT("instanceProperties"));
        const auto Authored=Properties->GetObjectField(TEXT("authoredProperties"));
        for (const TCHAR* Name:{TEXT("PhysMaterial"),TEXT("PhysicalMaterialMap"),TEXT("PhysMaterialMask"),
            TEXT("SubsurfaceProfile"),TEXT("SpecularProfileOverride"),TEXT("ToonProfileOverride"),TEXT("NeuralProfile"),
            TEXT("NaniteOverrideMaterial"),TEXT("BlendableLocationOverride"),TEXT("BlendablePriorityOverride"),
            TEXT("UserSceneTextureOverrides"),TEXT("EnumerationObjects"),TEXT("LightmassSettings"),
            TEXT("LayerParameterExpansion"),TEXT("ParameterOverviewExpansion")}) TestTrue(Name,Authored->HasField(Name));
        for (const TCHAR* Name:{TEXT("bOverridePhysMaterial"),TEXT("bOverrideSubsurfaceProfile"),TEXT("bOverrideSpecularProfile"),
            TEXT("bOverrideToonProfile"),TEXT("bOverrideBlendableLocation"),TEXT("bOverrideBlendablePriority")})
            TestTrue(Name,Authored->GetBoolField(Name));
        TestEqual(TEXT("Physical material map entry"),Authored->GetArrayField(TEXT("PhysicalMaterialMap"))[2]->AsString(),Instance->PhysicalMaterialMap[2]->GetPathName());
        TestFalse(TEXT("Authored Nanite override mode"),Authored->GetObjectField(TEXT("NaniteOverrideMaterial"))->GetBoolField(TEXT("bEnableOverride")));
        TestEqual(TEXT("Authored blendable priority"),Authored->GetIntegerField(TEXT("BlendablePriorityOverride")),11);
        TestEqual(TEXT("User scene texture inventory"),Authored->GetArrayField(TEXT("UserSceneTextureOverrides")).Num(),1);
        TestEqual(TEXT("Soft reference read without loading"),Authored->GetArrayField(TEXT("EnumerationObjects"))[0]->AsString(),FString(TEXT("/Game/Unloaded/Enumeration.Enumeration")));
        const auto Base=Properties->GetObjectField(TEXT("basePropertyOverrides"));
        TestEqual(TEXT("16 flags and 16 stored values"),Base->Values.Num(),32);
        for (const auto& Name:Flags) TestEqual(*Name,Base->GetBoolField(Name),Enabled);
        for (const auto& Name:BoolValues) TestTrue(*Name,Base->GetBoolField(Name));
        TestEqual(TEXT("Usage flag mask preserves high bits"),Base->GetNumberField(TEXT("bOverride_UsageFlags")),double(0xd2345678u));
        TestEqual(TEXT("Usage value mask preserves high bits"),Base->GetNumberField(TEXT("UsageFlags")),double(0xf1234567u));
        TestEqual(TEXT("Blend value retained while disabled"),Base->GetIntegerField(TEXT("BlendMode")),int32(BLEND_Masked));
        TestEqual(TEXT("Shading value retained"),Base->GetIntegerField(TEXT("ShadingModel")),int32(MSM_DefaultLit));
        TestEqual(TEXT("Opacity value retained"),Base->GetNumberField(TEXT("OpacityMaskClipValue")),.625);
        TestEqual(TEXT("WPO limit retained"),Base->GetNumberField(TEXT("MaxWorldPositionOffsetDisplacement")),127.);
        TestEqual(TEXT("Displacement magnitude"),Base->GetObjectField(TEXT("DisplacementScaling"))->GetNumberField(TEXT("Magnitude")),13.25);
        TestEqual(TEXT("Displacement center"),Base->GetObjectField(TEXT("DisplacementScaling"))->GetNumberField(TEXT("Center")),-.375);
        TestEqual(TEXT("Fade start"),Base->GetObjectField(TEXT("DisplacementFadeRange"))->GetNumberField(TEXT("StartSizePixels")),64.);
        TestEqual(TEXT("Fade end"),Base->GetObjectField(TEXT("DisplacementFadeRange"))->GetNumberField(TEXT("EndSizePixels")),32.);
        const auto V=Json->GetObjectField(TEXT("localOverrides"))->GetArrayField(TEXT("vector"))[0]->AsObject();
        TestEqual(TEXT("Live vector row has three keys"),V->Values.Num(),3);
        TestEqual(TEXT("Global association"),V->GetObjectField(TEXT("parameterInfo"))->GetStringField(TEXT("association")),FString(TEXT("GlobalParameter")));
        TestEqual(TEXT("Expression identity"),V->GetStringField(TEXT("expressionGuid")),Vector.ExpressionGUID.ToString());
        TestEqual(TEXT("Legacy name remains in copy witness"),Properties->GetArrayField(TEXT("legacyVectorParameterNames"))[0]->AsString(),FString(TEXT("LegacyTintEvidence")));
        TestEqual(TEXT("Local red tint"),V->GetArrayField(TEXT("value"))[0]->AsNumber(),double(Vector.ParameterValue.R));
        TestEqual(TEXT("Effective tint uses instance override"),Json->GetObjectField(TEXT("effectiveGlobalParameters"))->GetObjectField(TEXT("vector"))->GetArrayField(TEXT("Base_Color_Tint"))[0]->AsNumber(),double(Vector.ParameterValue.R));
        Stable=UWarImportLibrary::DescribeMaterialInstance(Instance);
        TestEqual(TEXT("Repeated readback stable"),UWarImportLibrary::DescribeMaterialInstance(Instance),Stable);
        TestEqual(TEXT("Package dirty bit unchanged"),Instance->GetPackage()->IsDirty(),WasDirty);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMaterialInstanceFamilies,"AegisWar.Foundation.CitadelMaterialInstanceFamilies",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarMaterialInstanceFamilies::RunTest(const FString&)
{
    auto* Instance=Fixture();const FMaterialParameterInfo P(TEXT("Extra"),LayerParameter,2);
    Instance->ScalarParameterValues.Emplace(P,1.5f);Instance->VectorParameterValues.Emplace(P,FLinearColor(.1f,.2f,.3f,.4f));
    Instance->DoubleVectorParameterValues.Emplace(P,FVector4d(1.25,2.5,3.75,4.));Instance->TextureParameterValues.Emplace(P,nullptr);
    Instance->TextureCollectionParameterValues.Emplace(P,nullptr);Instance->ParameterCollectionParameterValues.Emplace(P,nullptr);
    Instance->RuntimeVirtualTextureParameterValues.Emplace(P,nullptr);Instance->SparseVolumeTextureParameterValues.Emplace(P,nullptr);
    Instance->FontParameterValues.Emplace(P,nullptr,7);
    FStaticParameterSet Static;
    Static.StaticSwitchParameters.Emplace(P,true,true,FGuid(5,6,7,8));
    Static.StaticSwitchParameters.Emplace(FMaterialParameterInfo(TEXT("Disabled")),false,false,FGuid(8,7,6,5));
    Static.EditorOnly.StaticComponentMaskParameters.Emplace(P,true,false,true,false,false,FGuid(9,8,7,6));
    Static.EditorOnly.TerrainLayerWeightParameters.Emplace(FName(TEXT("Weight")),3);
    Static.EditorOnly.MaterialLayers.DeletedParentLayerGuids.Add(FGuid(1,1,2,2));
    // Unsaved fixture initialization retains disabled rows that SetPermutationParameters would trim.
    const auto* RuntimeProperty=FindFProperty<FStructProperty>(Instance->GetClass(),TEXT("StaticParametersRuntime"));
    if (!TestNotNull(TEXT("Runtime fixture property"),RuntimeProperty)) return false;
    *RuntimeProperty->ContainerPtrToValuePtr<FStaticParameterSetRuntimeData>(Instance)=Static.GetRuntime();
    Instance->GetEditorOnlyData()->StaticParameters=Static.EditorOnly;
    auto Json=ReadInstance(Instance);if (!TestTrue(TEXT("JSON"),Json.IsValid())) return false;
    TestTrue(TEXT("Every typed local family remains complete"),Json->GetBoolField(TEXT("overrideInventoryComplete")));
    TestFalse(TEXT("Layer globals are outside the bounded effective profile"),Json->GetBoolField(TEXT("available")));
    const auto Local=Json->GetObjectField(TEXT("localOverrides"));TestEqual(TEXT("Thirteen families"),Local->Values.Num(),13);
    for (const TCHAR* Family:{TEXT("scalar"),TEXT("vector"),TEXT("doubleVector"),TEXT("texture"),TEXT("textureCollection"),
        TEXT("parameterCollection"),TEXT("runtimeVirtualTexture"),TEXT("sparseVolumeTexture"),TEXT("font"),
        TEXT("staticComponentMask"),TEXT("terrainLayerWeight"),TEXT("materialLayers")})
        TestEqual(Family,Local->GetArrayField(Family).Num(),1);
    TestEqual(TEXT("Disabled switches retained"),Local->GetArrayField(TEXT("staticSwitch")).Num(),2);
    TestFalse(TEXT("Disabled switch flag observed"),Local->GetArrayField(TEXT("staticSwitch"))[1]->AsObject()->GetBoolField(TEXT("bOverride")));
    TestEqual(TEXT("Font page retained"),Local->GetArrayField(TEXT("font"))[0]->AsObject()->GetIntegerField(TEXT("FontPage")),7);
    TestEqual(TEXT("Layer association retained"),Local->GetArrayField(TEXT("vector"))[0]->AsObject()->GetObjectField(TEXT("parameterInfo"))->GetStringField(TEXT("association")),FString(TEXT("LayerParameter")));
    TestEqual(TEXT("Scalar value retained"),Local->GetArrayField(TEXT("scalar"))[0]->AsObject()->GetNumberField(TEXT("value")),1.5);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMaterialInstanceReadbackBounds,"AegisWar.Foundation.CitadelMaterialInstanceReadbackBounds",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarMaterialInstanceReadbackBounds::RunTest(const FString&)
{
    TestFalse(TEXT("Null rejected"),ReadInstance(nullptr)->GetBoolField(TEXT("available")));
    auto* Instance=Fixture();Instance->Parent=Instance;
    TestFalse(TEXT("Cycle rejected before parent traversal"),ReadInstance(Instance)->GetBoolField(TEXT("available")));
    Instance=Fixture();Instance->VectorParameterValues.SetNum(257);
    auto Json=ReadInstance(Instance);TestFalse(TEXT("Oversize inventory rejected without asserting"),Json->GetBoolField(TEXT("available")));
    TestFalse(TEXT("No truncation reported as complete"),Json->GetBoolField(TEXT("overrideInventoryComplete")));
    Instance=Fixture();Instance->BasePropertyOverrides.OpacityMaskClipValue=std::numeric_limits<float>::quiet_NaN();
    Json=ReadInstance(Instance);TestFalse(TEXT("Nonfinite stored value rejected"),Json->GetBoolField(TEXT("available")));
    TestFalse(TEXT("Nonfinite settings not complete"),Json->GetBoolField(TEXT("settingsInventoryComplete")));
    Instance=Fixture();
    auto* ImportProperty=FindFProperty<FObjectPropertyBase>(Instance->GetClass(),TEXT("AssetImportData"));
    if (!TestNotNull(TEXT("Import fixture property"),ImportProperty)) return false;
    ImportProperty->SetObjectPropertyValue_InContainer(Instance,NewObject<UAssetImportData>(Instance));
    TestFalse(TEXT("Unreflected inline authored payload cannot be reduced to a path"),ReadInstance(Instance)->GetBoolField(TEXT("settingsInventoryComplete")));
    Instance=Fixture();Instance->bHasStaticPermutationResource=true;
    TestTrue(TEXT("Static resource flag read directly"),ReadInstance(Instance)->GetBoolField(TEXT("hasStaticPermutationResource")));
    // No resource is created or queried by this descriptor.
    Instance->bHasStaticPermutationResource=false;
    return true;
}
#endif
