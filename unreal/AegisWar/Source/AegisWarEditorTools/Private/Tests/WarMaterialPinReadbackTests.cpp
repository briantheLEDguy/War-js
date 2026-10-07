#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarImportLibrary.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionMultiply.h"
#include "Materials/MaterialExpressionTextureSample.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarMaterialPinReadbackTest,"AegisWar.Foundation.CitadelMaterialPins",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarMaterialPinReadbackTest::RunTest(const FString& Parameters)
{
    auto* Package=CreatePackage(TEXT("/Temp/WarMaterialPinReadback"));
    auto* Material=NewObject<UMaterial>(Package);
    auto* Texture=NewObject<UMaterialExpressionTextureSample>(Material);
    auto* Multiply=NewObject<UMaterialExpressionMultiply>(Material);
    Multiply->A.Connect(3,Texture);
    const FExpressionInput BeforeA=Multiply->A,BeforeB=Multiply->B;
    const bool bDirty=Package->IsDirty();
    const auto Parse=[this](const FString& Json)
    {
        TSharedPtr<FJsonObject> Report;
        TestTrue(TEXT("Native pin report is JSON"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Report));
        return Report;
    };
    const auto Report=Parse(UWarImportLibrary::DescribeMaterialExpressionPins(Multiply));
    if (!Report) return false;
    TestTrue(TEXT("Readback is explicitly read only"),Report->GetBoolField(TEXT("readOnly")));
    TestTrue(TEXT("Valid native expression is available"),Report->GetBoolField(TEXT("available")));
    TestEqual(TEXT("Report is bound to actual expression"),Report->GetStringField(TEXT("expression")),Multiply->GetPathName());
    const auto Inputs=Report->GetArrayField(TEXT("inputs"));
    if (!TestEqual(TEXT("Both connected and disconnected pins are present"),Inputs.Num(),2)) return false;
    const auto A=Inputs[0]->AsObject(),B=Inputs[1]->AsObject();
    TestEqual(TEXT("Pin position is retained"),A->GetIntegerField(TEXT("inputIndex")),0);
    TestEqual(TEXT("Actual source node is retained"),A->GetStringField(TEXT("node")),Texture->GetName());
    TestEqual(TEXT("Channel-specific source output is retained"),A->GetIntegerField(TEXT("output_index")),3);
    TestEqual(TEXT("Pin name is read from native accessor"),A->GetStringField(TEXT("input_name")),Multiply->GetInputName(0).ToString());
    TestTrue(TEXT("Disconnected source is explicitly null"),B->TryGetField(TEXT("node"))->Type==EJson::Null);
    const TCHAR* MaskKeys[]={TEXT("mask"),TEXT("mask_r"),TEXT("mask_g"),TEXT("mask_b"),TEXT("mask_a")};
    const int32 BeforeMasks[]={BeforeA.Mask,BeforeA.MaskR,BeforeA.MaskG,BeforeA.MaskB,BeforeA.MaskA};
    for (int32 Index=0;Index<UE_ARRAY_COUNT(MaskKeys);++Index)
        TestEqual(TEXT("Exact channel mask is retained"),A->GetIntegerField(MaskKeys[Index]),BeforeMasks[Index]);
    const auto TextureReport=Parse(UWarImportLibrary::DescribeMaterialExpressionPins(Texture));
    if (!TextureReport) return false;
    const auto Outputs=TextureReport->GetArrayField(TEXT("outputs"));
    TestEqual(TEXT("Every native output is read"),Outputs.Num(),Texture->GetOutputs().Num());
    for (int32 Index=0;Index<Outputs.Num();++Index)
    {
        const auto Row=Outputs[Index]->AsObject();const auto& Native=Texture->GetOutputs()[Index];
        const int32 Masks[]={Native.Mask,Native.MaskR,Native.MaskG,Native.MaskB,Native.MaskA};
        for (int32 Mask=0;Mask<UE_ARRAY_COUNT(MaskKeys);++Mask)
            TestEqual(TEXT("Actual output masks are retained"),Row->GetIntegerField(MaskKeys[Mask]),Masks[Mask]);
    }
    TestTrue(TEXT("Repeated read is stable"),UWarImportLibrary::DescribeMaterialExpressionPins(Multiply)==UWarImportLibrary::DescribeMaterialExpressionPins(Multiply));
    TestTrue(TEXT("Source connection and output are unchanged"),Multiply->A.Expression==BeforeA.Expression && Multiply->A.OutputIndex==BeforeA.OutputIndex);
    TestTrue(TEXT("Disconnected input is unchanged"),Multiply->B.Expression==BeforeB.Expression && Multiply->B.OutputIndex==BeforeB.OutputIndex);
    TestEqual(TEXT("Package dirtiness is unchanged"),Package->IsDirty(),bDirty);
    Material->GetExpressionInputForProperty(MP_BaseColor)->Connect(0,Multiply);
    Material->GetExpressionInputForProperty(MP_PixelDepthOffset)->Connect(1,Texture);
    Material->GetExpressionInputForProperty(MP_CustomizedUVs3)->Connect(2,Texture);
    const bool bRootDirty=Package->IsDirty();
    const auto RootsReport=Parse(UWarImportLibrary::DescribeMaterialRoots(Material));
    if (!RootsReport) return false;
    TestTrue(TEXT("Native hidden roots are available"),RootsReport->GetBoolField(TEXT("available")));
    const auto Roots=RootsReport->GetObjectField(TEXT("roots"));
    TestEqual(TEXT("All preserved roots and eight customized UVs are present"),Roots->Values.Num(),21);
    TestEqual(TEXT("Hidden pixel-depth source channel is exact"),Roots->GetObjectField(TEXT("MP_PIXEL_DEPTH_OFFSET"))->GetIntegerField(TEXT("output_index")),1);
    TestEqual(TEXT("Customized UV source channel is exact"),Roots->GetObjectField(TEXT("MP_CUSTOMIZED_UVS3"))->GetIntegerField(TEXT("output_index")),2);
    TestTrue(TEXT("Disconnected displacement is recorded"),Roots->GetObjectField(TEXT("MP_DISPLACEMENT"))->TryGetField(TEXT("node"))->Type==EJson::Null);
    TestTrue(TEXT("Hidden-root readback preserves the source"),Material->GetExpressionInputForProperty(MP_PixelDepthOffset)->Expression==Texture);
    TestEqual(TEXT("Root inspection does not dirty the package"),Package->IsDirty(),bRootDirty);
    const auto MissingRoots=Parse(UWarImportLibrary::DescribeMaterialRoots(nullptr));
    if (!MissingRoots) return false;
    TestFalse(TEXT("Invalid material has no invented roots"),MissingRoots->GetBoolField(TEXT("available")));
    const auto Missing=Parse(UWarImportLibrary::DescribeMaterialExpressionPins(nullptr));
    if (!Missing) return false;
    TestFalse(TEXT("Invalid expression cannot invent a graph"),Missing->GetBoolField(TEXT("available")));
    Texture->MarkAsGarbage();
    const auto Dangling=Parse(UWarImportLibrary::DescribeMaterialExpressionPins(Multiply));
    if (!Dangling) return false;
    TestFalse(TEXT("Invalid upstream node rejects complete readback"),Dangling->GetBoolField(TEXT("available")));
    Texture->ClearGarbage();return true;
}
#endif
